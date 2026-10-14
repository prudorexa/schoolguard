"""
fees/services.py

Per the blueprint's layering rule: views call these, never touch models
directly for anything that changes money state. Two functions here matter
most:

- create_invoice_for_student: computes total_amount from line items --
  never accepts a client-supplied total, so the number on an invoice is
  always the sum of what's actually itemized.
- record_payment: the reconciliation logic lives here. It rejects a
  payment that would push the invoice past its total (no silent
  overpayment sitting unexplained in the system), and recomputes
  Invoice.status from the real payment total after every payment --
  status is never set directly by a client or a view.
"""

from decimal import Decimal

from django.db import transaction

from audit.services import log_action

from .models import FeeCategory, Invoice, InvoiceItem, Payment, Receipt


class InvoiceValidationError(Exception):
    pass


class PaymentValidationError(Exception):
    pass


@transaction.atomic
def create_invoice_for_student(*, school, student, term, items: list[dict]) -> Invoice:
    """
    items: [{"fee_category_id": int, "description": str, "amount": Decimal}, ...]
    """
    if not items:
        raise InvoiceValidationError("An invoice must have at least one line item.")

    total = sum((Decimal(str(item["amount"])) for item in items), Decimal("0.00"))
    if total <= 0:
        raise InvoiceValidationError("Invoice total must be greater than zero.")

    invoice = Invoice.objects.create(school=school, student=student, term=term, total_amount=total)

    invoice_items = []
    for item in items:
        fee_category = FeeCategory.objects.get(id=item["fee_category_id"], school=school)
        invoice_items.append(
            InvoiceItem(
                school=school,
                invoice=invoice,
                fee_category=fee_category,
                description=item.get("description", ""),
                amount=Decimal(str(item["amount"])),
            )
        )
    InvoiceItem.objects.bulk_create(invoice_items)

    return invoice


def _recompute_invoice_status(invoice: Invoice) -> None:
    if invoice.status == "cancelled":
        return
    paid = invoice.amount_paid
    if paid <= 0:
        invoice.status = "issued"
    elif paid < invoice.total_amount:
        invoice.status = "partially_paid"
    else:
        invoice.status = "paid"
    invoice.save(update_fields=["status"])


def _next_receipt_number(school) -> str:
    count = Receipt.objects.filter(school=school).count() + 1
    return f"RCT-{school.code}-{count:06d}"


@transaction.atomic
def record_payment(*, school, invoice: Invoice, amount: Decimal, method: str, reference_number: str, recorded_by) -> Payment:
    if invoice.school_id != school.id:
        raise PaymentValidationError("Invoice does not belong to this school.")
    if invoice.status == "cancelled":
        raise PaymentValidationError("Cannot record a payment against a cancelled invoice.")

    amount = Decimal(str(amount))
    if amount <= 0:
        raise PaymentValidationError("Payment amount must be greater than zero.")

    outstanding = invoice.balance
    if amount > outstanding:
        raise PaymentValidationError(
            f"Payment of {amount} exceeds the outstanding balance of {outstanding} on this invoice."
        )

    payment = Payment.objects.create(
        school=school,
        invoice=invoice,
        amount=amount,
        method=method,
        reference_number=reference_number,
        recorded_by=recorded_by,
        status="completed",
    )
    Receipt.objects.create(school=school, payment=payment, receipt_number=_next_receipt_number(school))

    _recompute_invoice_status(invoice)

    log_action(
        school=school, user=recorded_by, action="payment.recorded",
        entity_type="Payment", entity_id=payment.id,
        new_value={"invoice_id": invoice.id, "amount": amount, "method": method, "reference_number": reference_number},
    )

    return payment


@transaction.atomic
def reverse_payment(*, payment: Payment, reason: str, actor) -> Payment:
    """
    Never deletes the payment -- flips it to `reversed` with a required
    reason and recomputes the invoice's status/balance from what's left.
    This is the "reversal mechanism instead of deletion" the blueprint's
    audit principle requires.
    """
    if not reason.strip():
        raise PaymentValidationError("A reason is required to reverse a payment.")
    if payment.status == "reversed":
        raise PaymentValidationError("Payment is already reversed.")

    previous_status = payment.status
    payment.status = "reversed"
    payment.reversal_reason = reason
    payment.save(update_fields=["status", "reversal_reason"])

    _recompute_invoice_status(payment.invoice)

    log_action(
        school=payment.school, user=actor, action="payment.reversed",
        entity_type="Payment", entity_id=payment.id, reason=reason,
        previous_value={"status": previous_status}, new_value={"status": "reversed"},
    )

    return payment
