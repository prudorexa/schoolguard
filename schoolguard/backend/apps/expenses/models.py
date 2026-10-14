"""
expenses/models.py

Status machine (matches the blueprint exactly):
  draft -> pending_approval -> approved -> paid
                             -> rejected  (from pending_approval)
  draft / pending_approval -> cancelled

All transitions happen in services.py, never via a raw field write from a
view or client -- see ExpenseViewSet's http_method_names restriction and
the dedicated action endpoints (submit/approve/reject/mark_paid/cancel).

`amount` is computed from ExpenseItem lines, same pattern as
Invoice.total_amount in the fees app -- never client-set directly.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from schools.models import Department, Term, TenantScopedModel


class Expense(TenantScopedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="expenses")
    # Explicit, not inferred from created_at -- budgets/services.py filters
    # spend by this field. Inferring "which term" from wall-clock creation
    # time is fragile (an expense entered a few days after term-end
    # wouldn't count toward that term's budget); nullable because not every
    # expense is necessarily budget-tracked.
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="expenses_requested"
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"


class ExpenseItem(TenantScopedModel):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    def __str__(self) -> str:
        return f"{self.description}: {self.amount}"
