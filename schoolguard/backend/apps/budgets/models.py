"""
budgets/models.py

Budget only stores what's actually allocated -- allocated_amount, plus
which department/term it covers. `spent_amount` is NOT a stored field:
it's computed in services.py from real Expense rows (status in
approved/paid) for that department+term, so it can never drift from
reality the way a manually-incremented counter could.
"""

from decimal import Decimal

from django.db import models

from schools.models import Department, Term, TenantScopedModel


class Budget(TenantScopedModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="budgets")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="budgets")
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Warn once utilization crosses this percentage, flag once it exceeds 100%.
    warning_threshold_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("80.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["term", "department"], name="unique_budget_per_term_and_department"),
        ]
        ordering = ["-term__start_date", "department__name"]

    def __str__(self) -> str:
        return f"{self.department.name} / {self.term.name}: {self.allocated_amount}"
