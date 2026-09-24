"""
procurement/models.py

Pipeline: PurchaseRequest -> Quotation(s) -> PurchaseOrder (from the
selected quotation) -> Delivery -> SupplierInvoice.

The point of this module (blueprint section 13) is being able to compare
requested vs approved vs delivered vs invoiced vs paid and flag mismatches
-- so PurchaseOrder.amount is fixed at issue time (from the selected
quotation), Delivery and SupplierInvoice are separate records against that
PO rather than editable fields on it, and the discrepancy check
(PurchaseOrder.invoice_discrepancy) compares the PO amount to whatever
actually got invoiced.

Same status-machine discipline as expenses/models.py: every transition
happens in services.py, nothing is a raw field write from a view.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from schools.models import Department, TenantScopedModel


class PurchaseRequest(TenantScopedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("converted", "Converted to Purchase Order"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="purchase_requests")
    estimated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    requested_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="purchase_requests_made")
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase_requests_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"


class PurchaseRequestItem(TenantScopedModel):
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    estimated_unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    @property
    def estimated_total(self) -> Decimal:
        return self.estimated_unit_price * self.quantity

    def __str__(self) -> str:
        return f"{self.description} x{self.quantity}"


class Quotation(TenantScopedModel):
    """Multiple suppliers can quote against the same (approved) purchase
    request; exactly one gets selected when the PO is issued."""

    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="quotations")
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="quotations")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    notes = models.CharField(max_length=255, blank=True)
    submitted_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="quotations_submitted")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["purchase_request", "supplier"], name="unique_quotation_per_supplier_per_request"),
        ]
        ordering = ["amount"]

    def __str__(self) -> str:
        return f"{self.supplier.name}: {self.amount}"


class PurchaseOrder(TenantScopedModel):
    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    purchase_request = models.OneToOneField(PurchaseRequest, on_delete=models.PROTECT, related_name="purchase_order")
    selected_quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="purchase_order")
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_orders")
    # Fixed at issue time from selected_quotation.amount -- the anchor
    # figure everything downstream (delivery, invoice) gets compared to.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="issued")
    issued_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="purchase_orders_issued")
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"PO-{self.id} {self.supplier.name} ({self.amount})"


class Delivery(TenantScopedModel):
    purchase_order = models.OneToOneField(PurchaseOrder, on_delete=models.PROTECT, related_name="delivery")
    is_complete = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)
    received_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="deliveries_received")
    delivered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Delivery for PO-{self.purchase_order_id}"


class SupplierInvoice(TenantScopedModel):
    """The supplier's actual invoice for the PO. `amount` here is what's
    compared against PurchaseOrder.amount to flag a mismatch -- see
    PurchaseOrder-adjacent discrepancy check in services.py."""

    purchase_order = models.OneToOneField(PurchaseOrder, on_delete=models.PROTECT, related_name="supplier_invoice")
    invoice_number = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="supplier_invoices_recorded")
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Invoice {self.invoice_number or self.id} for PO-{self.purchase_order_id}"
