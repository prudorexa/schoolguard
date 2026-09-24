"""
expenses/services.py

The workflow lives here, not in views. Two rules are enforced independent
of the caller's role/permission -- meaning even a School Admin with every
permission in the system still can't do these:

1. A user can never approve or reject their own expense request
   (self.requested_by == approver is checked regardless of what
   fees.approve_expenses-equivalent permission the approver holds).
2. Status transitions only happen along the documented graph -- e.g.
   approve() only works from pending_approval, mark_paid() only from
   approved. There's no path from draft straight to paid.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.services import log_action

from .models import Expense, ExpenseItem


class ExpenseValidationError(Exception):
    pass


class ExpenseWorkflowError(Exception):
    pass


@transaction.atomic
def create_expense_request(*, school, title, department, supplier, term=None, requested_by, items: list[dict]) -> Expense:
    """Creates in `draft` status -- the requester can add/edit items before
    submitting. items: [{"description": str, "amount": Decimal}, ...]"""
    if not items:
        raise ExpenseValidationError("An expense request must have at least one line item.")

    total = sum((Decimal(str(item["amount"])) for item in items), Decimal("0.00"))
    if total <= 0:
        raise ExpenseValidationError("Expense total must be greater than zero.")

    expense = Expense.objects.create(
        school=school, title=title, department=department, supplier=supplier, term=term,
        amount=total, requested_by=requested_by, status="draft",
    )
    ExpenseItem.objects.bulk_create(
        ExpenseItem(school=school, expense=expense, description=item["description"], amount=Decimal(str(item["amount"])))
        for item in items
    )
    return expense


def submit_for_approval(*, expense: Expense) -> Expense:
    if expense.status != "draft":
        raise ExpenseWorkflowError(f"Cannot submit an expense in '{expense.status}' status.")
    expense.status = "pending_approval"
    expense.save(update_fields=["status"])
    return expense


def approve_expense(*, expense: Expense, approver) -> Expense:
    if expense.status != "pending_approval":
        raise ExpenseWorkflowError(f"Cannot approve an expense in '{expense.status}' status.")
    if expense.requested_by_id == approver.id:
        # Enforced here, unconditionally -- not a permission check, because
        # no permission should be able to override this rule.
        raise ExpenseWorkflowError("You cannot approve your own expense request.")

    expense.status = "approved"
    expense.approved_by = approver
    expense.approved_at = timezone.now()
    expense.save(update_fields=["status", "approved_by", "approved_at"])

    log_action(
        school=expense.school, user=approver, action="expense.approved",
        entity_type="Expense", entity_id=expense.id,
        previous_value={"status": "pending_approval"}, new_value={"status": "approved", "amount": expense.amount},
    )
    return expense


def reject_expense(*, expense: Expense, approver, reason: str) -> Expense:
    if expense.status != "pending_approval":
        raise ExpenseWorkflowError(f"Cannot reject an expense in '{expense.status}' status.")
    if expense.requested_by_id == approver.id:
        raise ExpenseWorkflowError("You cannot reject your own expense request.")
    if not reason.strip():
        raise ExpenseValidationError("A reason is required to reject an expense.")

    expense.status = "rejected"
    expense.approved_by = approver
    expense.approved_at = timezone.now()
    expense.rejection_reason = reason
    expense.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason"])

    log_action(
        school=expense.school, user=approver, action="expense.rejected",
        entity_type="Expense", entity_id=expense.id, reason=reason,
        previous_value={"status": "pending_approval"}, new_value={"status": "rejected"},
    )
    return expense


def mark_expense_paid(*, expense: Expense, actor) -> Expense:
    if expense.status != "approved":
        raise ExpenseWorkflowError(f"Cannot mark an expense paid from '{expense.status}' status -- it must be approved first.")
    expense.status = "paid"
    expense.paid_at = timezone.now()
    expense.save(update_fields=["status", "paid_at"])

    log_action(
        school=expense.school, user=actor, action="expense.paid",
        entity_type="Expense", entity_id=expense.id,
        previous_value={"status": "approved"}, new_value={"status": "paid", "amount": expense.amount},
    )
    return expense


def cancel_expense(*, expense: Expense, actor) -> Expense:
    if expense.status not in ("draft", "pending_approval"):
        raise ExpenseWorkflowError(f"Cannot cancel an expense already in '{expense.status}' status.")
    expense.status = "cancelled"
    expense.save(update_fields=["status"])
    return expense
