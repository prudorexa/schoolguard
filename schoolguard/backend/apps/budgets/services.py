"""
budgets/services.py

`budget_status(budget)` is read-only and computed fresh every call --
spent_amount sums real Expense rows rather than trusting a stored counter.
Only expenses with status 'approved' or 'paid' count as spend (a 'draft' or
'pending_approval' expense hasn't committed any money yet; 'rejected'/
'cancelled' never will). This mirrors the blueprint's
allocated -> spent -> remaining -> utilization% -> warn-near/over-budget
requirement directly against real transactional data.
"""

from decimal import Decimal

from django.db.models import Sum

from expenses.models import Expense

from .models import Budget

COMMITTED_EXPENSE_STATUSES = ["approved", "paid"]


def budget_status(*, budget: Budget) -> dict:
    spent = (
        Expense.objects.filter(
            school=budget.school,
            department=budget.department,
            term=budget.term,
            status__in=COMMITTED_EXPENSE_STATUSES,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    allocated = budget.allocated_amount
    remaining = allocated - spent
    utilization_pct = (spent / allocated * 100) if allocated > 0 else Decimal("0.00")

    return {
        "budget_id": budget.id,
        "department": budget.department.name,
        "term": budget.term.name,
        "allocated_amount": allocated,
        "spent_amount": spent,
        "remaining_amount": remaining,
        "utilization_pct": utilization_pct.quantize(Decimal("0.01")),
        "is_over_budget": spent > allocated,
        "is_near_threshold": not (spent > allocated) and utilization_pct >= budget.warning_threshold_pct,
    }
