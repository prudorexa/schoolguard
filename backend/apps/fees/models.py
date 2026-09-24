"""
fees/models.py

Money starts here, so a few things are deliberate:

- Amounts are DecimalField, never float -- floats lose cents over enough
  transactions, which is exactly the kind of "small unexplained drift" this
  whole product exists to catch, so it can't be baked into the schema.
- Invoice.status and Payment are never mutated directly by a view -- see
  services.py. The models just hold state; services.py is the only place
  that's allowed to change it, and every change recomputes status from the
  actual payment total rather than trusting a client-sent status.
- Nothing here gets hard-deleted. A wrong payment gets reversed (status
  change + a linked reversal note), not removed -- the blueprint's audit
  principle applies even before the dedicated audit_logs table exists
  (Phase 5); this phase just doesn't erase its own history.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from schools.models import Class, Term, TenantScopedModel
from students.models import Student


class FeeCategory(TenantScopedModel):
    """e.g. Tuition, Transport, Lunch."""

    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_fee_category_per_school"),
        ]
        verbose_name_plural = "fee categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FeeStructure(TenantScopedModel):
    """
    What a given fee category costs for a term (optionally narrowed to one
    class -- e.g. "Grade 4 Transport" priced differently from "Grade 1
    Transport"). This is the template; Invoice/InvoiceItem below are the
    actual per-student charges generated from it.
    """

    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="fee_structures")
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.PROTECT, related_name="fee_structures")
    school_class = models.ForeignKey(
        Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="fee_structures"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["term", "fee_category", "school_class"], name="unique_fee_structure_per_term_category_class"
            ),
        ]

    def __str__(self) -> str:
        scope = self.school_class.name if self.school_class_id else "All classes"
        return f"{self.fee_category.name} - {self.term.name} ({scope})"


class Invoice(TenantScopedModel):
    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="invoices")
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="invoices")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="issued")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invoice #{self.id} - {self.student} ({self.term})"

    @property
    def amount_paid(self) -> Decimal:
        total = self.payments.filter(status="completed").aggregate(total=models.Sum("amount"))["total"]
        return total or Decimal("0.00")

    @property
    def balance(self) -> Decimal:
        return self.total_amount - self.amount_paid


class InvoiceItem(TenantScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.PROTECT, related_name="invoice_items")
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    def __str__(self) -> str:
        return f"{self.fee_category.name}: {self.amount}"


class Payment(TenantScopedModel):
    METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("bank_transfer", "Bank Transfer"),
        ("card", "Card"),
        ("cash", "Cash"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("reversed", "Reversed"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="payments_recorded")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="completed")
    reversal_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self) -> str:
        return f"Payment of {self.amount} on Invoice #{self.invoice_id}"


class Receipt(TenantScopedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField(max_length=40, unique=True)

    def __str__(self) -> str:
        return self.receipt_number
