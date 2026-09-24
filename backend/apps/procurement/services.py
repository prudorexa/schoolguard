"""
procurement/services.py

Two things matter here:

1. Same self-approval block as expenses -- a requester can never approve
   their own purchase request, enforced unconditionally regardless of the
   approver's permissions.
2. `discrepancy_report(purchase_order)` is the actual point of this module
   per the blueprint: compare estimated (from the PR) vs approved (PR at
   approval time -- we don't let estimated change after approval, so these
   are the same field) vs PO amount (from the selected quotation) vs
   invoiced amount, and flag anything that doesn't line up. This returns
   data for a human to review -- it never blocks a transition or accuses
   anyone of anything, matching the blueprint's "flag for human review,
   never auto-accuse" principle from the AI section, applied here too.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.services import log_action

from .models import Delivery, PurchaseOrder, PurchaseRequest, PurchaseRequestItem, Quotation, SupplierInvoice

DISCREPANCY_THRESHOLD_PCT = Decimal("5.0")  # flag if invoice differs from PO amount by more than this %


class ProcurementValidationError(Exception):
    pass


class ProcurementWorkflowError(Exception):
    pass


@transaction.atomic
def create_purchase_request(*, school, title, department, requested_by, items: list[dict]) -> PurchaseRequest:
    if not items:
        raise ProcurementValidationError("A purchase request must have at least one line item.")

    pr = PurchaseRequest.objects.create(
        school=school, title=title, department=department, requested_by=requested_by, status="draft",
    )
    PurchaseRequestItem.objects.bulk_create(
        PurchaseRequestItem(
            school=school, purchase_request=pr,
            description=item["description"], quantity=item["quantity"], estimated_unit_price=Decimal(str(item["unit_price"])),
        )
        for item in items
    )
    pr.estimated_amount = sum((i.estimated_total for i in pr.items.all()), Decimal("0.00"))
    pr.save(update_fields=["estimated_amount"])
    return pr


def submit_for_approval(*, purchase_request: PurchaseRequest) -> PurchaseRequest:
    if purchase_request.status != "draft":
        raise ProcurementWorkflowError(f"Cannot submit a purchase request in '{purchase_request.status}' status.")
    purchase_request.status = "pending_approval"
    purchase_request.save(update_fields=["status"])
    return purchase_request


def approve_purchase_request(*, purchase_request: PurchaseRequest, approver) -> PurchaseRequest:
    if purchase_request.status != "pending_approval":
        raise ProcurementWorkflowError(f"Cannot approve a purchase request in '{purchase_request.status}' status.")
    if purchase_request.requested_by_id == approver.id:
        raise ProcurementWorkflowError("You cannot approve your own purchase request.")

    purchase_request.status = "approved"
    purchase_request.approved_by = approver
    purchase_request.approved_at = timezone.now()
    purchase_request.save(update_fields=["status", "approved_by", "approved_at"])

    log_action(
        school=purchase_request.school, user=approver, action="purchase_request.approved",
        entity_type="PurchaseRequest", entity_id=purchase_request.id,
        previous_value={"status": "pending_approval"},
        new_value={"status": "approved", "estimated_amount": purchase_request.estimated_amount},
    )
    return purchase_request


def reject_purchase_request(*, purchase_request: PurchaseRequest, approver, reason: str) -> PurchaseRequest:
    if purchase_request.status != "pending_approval":
        raise ProcurementWorkflowError(f"Cannot reject a purchase request in '{purchase_request.status}' status.")
    if purchase_request.requested_by_id == approver.id:
        raise ProcurementWorkflowError("You cannot reject your own purchase request.")
    if not reason.strip():
        raise ProcurementValidationError("A reason is required to reject a purchase request.")

    purchase_request.status = "rejected"
    purchase_request.approved_by = approver
    purchase_request.approved_at = timezone.now()
    purchase_request.rejection_reason = reason
    purchase_request.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason"])

    log_action(
        school=purchase_request.school, user=approver, action="purchase_request.rejected",
        entity_type="PurchaseRequest", entity_id=purchase_request.id, reason=reason,
        previous_value={"status": "pending_approval"}, new_value={"status": "rejected"},
    )
    return purchase_request


def submit_quotation(*, school, purchase_request: PurchaseRequest, supplier, amount: Decimal, notes: str, submitted_by) -> Quotation:
    if purchase_request.status != "approved":
        raise ProcurementWorkflowError("Quotations can only be submitted against an approved purchase request.")
    return Quotation.objects.create(
        school=school, purchase_request=purchase_request, supplier=supplier,
        amount=amount, notes=notes, submitted_by=submitted_by,
    )


@transaction.atomic
def issue_purchase_order(*, purchase_request: PurchaseRequest, quotation: Quotation, issued_by) -> PurchaseOrder:
    if purchase_request.status != "approved":
        raise ProcurementWorkflowError(f"Cannot issue a PO from a purchase request in '{purchase_request.status}' status.")
    if quotation.purchase_request_id != purchase_request.id:
        raise ProcurementValidationError("Quotation does not belong to this purchase request.")
    if hasattr(purchase_request, "purchase_order"):
        raise ProcurementWorkflowError("A purchase order has already been issued for this purchase request.")

    po = PurchaseOrder.objects.create(
        school=purchase_request.school, purchase_request=purchase_request, selected_quotation=quotation,
        supplier=quotation.supplier, amount=quotation.amount, issued_by=issued_by,
    )
    purchase_request.status = "converted"
    purchase_request.save(update_fields=["status"])

    log_action(
        school=po.school, user=issued_by, action="purchase_order.issued",
        entity_type="PurchaseOrder", entity_id=po.id,
        new_value={"supplier_id": quotation.supplier_id, "amount": po.amount, "purchase_request_id": purchase_request.id},
    )
    return po


def record_delivery(*, purchase_order: PurchaseOrder, is_complete: bool, notes: str, received_by) -> Delivery:
    if purchase_order.status != "issued":
        raise ProcurementWorkflowError(f"Cannot record delivery for a PO in '{purchase_order.status}' status.")
    if hasattr(purchase_order, "delivery"):
        raise ProcurementWorkflowError("A delivery has already been recorded for this purchase order.")

    delivery = Delivery.objects.create(
        school=purchase_order.school, purchase_order=purchase_order,
        is_complete=is_complete, notes=notes, received_by=received_by,
    )
    if is_complete:
        purchase_order.status = "delivered"
        purchase_order.save(update_fields=["status"])
    return delivery


def record_supplier_invoice(*, purchase_order: PurchaseOrder, invoice_number: str, amount: Decimal, recorded_by) -> SupplierInvoice:
    if hasattr(purchase_order, "supplier_invoice"):
        raise ProcurementWorkflowError("A supplier invoice has already been recorded for this purchase order.")
    return SupplierInvoice.objects.create(
        school=purchase_order.school, purchase_order=purchase_order,
        invoice_number=invoice_number, amount=amount, recorded_by=recorded_by,
    )


def discrepancy_report(*, purchase_order: PurchaseOrder) -> dict:
    """
    Read-only comparison across the pipeline -- never blocks anything,
    never accuses anyone, just surfaces numbers for a human to review
    (matching the blueprint's "flag for human review" principle).
    """
    pr = purchase_order.purchase_request
    invoice = getattr(purchase_order, "supplier_invoice", None)
    delivery = getattr(purchase_order, "delivery", None)

    report = {
        "requested_amount": pr.estimated_amount,
        "po_amount": purchase_order.amount,
        "invoiced_amount": invoice.amount if invoice else None,
        "delivered": delivery.is_complete if delivery else False,
        "flags": [],
    }

    if invoice is not None and purchase_order.amount > 0:
        variance_pct = abs(invoice.amount - purchase_order.amount) / purchase_order.amount * 100
        if variance_pct > DISCREPANCY_THRESHOLD_PCT:
            report["flags"].append(
                f"Invoice amount ({invoice.amount}) differs from PO amount ({purchase_order.amount}) "
                f"by {variance_pct:.1f}%, above the {DISCREPANCY_THRESHOLD_PCT}% threshold."
            )

    if invoice is not None and delivery is None:
        report["flags"].append("Supplier invoice recorded but no delivery has been confirmed yet.")

    return report
