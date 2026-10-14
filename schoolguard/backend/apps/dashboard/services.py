"""
dashboard/services.py

Everything here is read-only and computed at request time from the
transactional apps (fees, expenses, procurement, budgets) -- there is
nothing to keep in sync because nothing is stored. At real scale this
would move to aggregation tables refreshed on a schedule (flagged in the
blueprint's own performance NFR), but computing fresh is the right default
until there's a measured reason not to.

financial_alerts() deliberately does NOT include a statistical "unusual
spending" alert -- that requires a baseline/model and belongs to the AI
anomaly-detection layer (blueprint Phase 7), not hand-rolled here. Every
alert below is plain arithmetic against a documented rule, matching the
blueprint's explicit example ("Expense is 72% higher than average" is a
model's job; "budget exceeded" and "invoice doesn't match PO" are not).
"""

from datetime import date
from decimal import Decimal
from itertools import groupby

from django.db.models import Sum

from budgets.models import Budget
from budgets.services import budget_status
from expenses.models import Expense
from fees.models import Invoice, Payment
from procurement.models import PurchaseOrder
from procurement.services import discrepancy_report


def financial_summary(*, school) -> dict:
    total_collected = (
        Payment.objects.filter(school=school, status="completed").aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    total_expenses = (
        Expense.objects.filter(school=school, status="paid").aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # Invoice.balance is a Python property (total_amount - amount_paid via
    # completed payments), so outstanding fees are summed in Python rather
    # than a single SQL aggregate -- fine at this scale; worth revisiting
    # with a denormalized column if invoice volume grows large.
    outstanding_fees = sum(
        (inv.balance for inv in Invoice.objects.filter(school=school).exclude(status="cancelled")),
        Decimal("0.00"),
    )

    budgets = list(Budget.objects.filter(school=school).select_related("department", "term"))
    budget_reports = [budget_status(budget=b) for b in budgets]
    total_allocated = sum((r["allocated_amount"] for r in budget_reports), Decimal("0.00"))
    total_spent = sum((r["spent_amount"] for r in budget_reports), Decimal("0.00"))
    overall_utilization_pct = (
        (total_spent / total_allocated * 100).quantize(Decimal("0.01")) if total_allocated > 0 else Decimal("0.00")
    )

    pending_expense_approvals = Expense.objects.filter(school=school, status="pending_approval").count()

    recent_payments = list(
        Payment.objects.filter(school=school, status="completed").select_related("invoice__student").order_by("-paid_at")[:5]
    )
    recent_expense_payments = list(
        Expense.objects.filter(school=school, status="paid").order_by("-paid_at")[:5]
    )

    recent_transactions = sorted(
        [
            {"type": "fee_payment", "id": p.id, "amount": p.amount, "date": p.paid_at, "description": f"Payment on invoice #{p.invoice_id}"}
            for p in recent_payments
        ]
        + [
            {"type": "expense_paid", "id": e.id, "amount": e.amount, "date": e.paid_at, "description": e.title}
            for e in recent_expense_payments
        ],
        key=lambda row: row["date"] or date.min,
        reverse=True,
    )[:10]

    return {
        "total_collected": total_collected,
        "total_expenses": total_expenses,
        "outstanding_fees": outstanding_fees,
        "net_position": total_collected - total_expenses,
        "budget_allocated": total_allocated,
        "budget_spent": total_spent,
        "budget_utilization_pct": overall_utilization_pct,
        "pending_expense_approvals": pending_expense_approvals,
        "recent_transactions": recent_transactions,
    }


DUPLICATE_PAYMENT_WINDOW_HOURS = 24


def financial_alerts(*, school) -> list[dict]:
    """
    Every alert is a plain rule against real rows, never a model output --
    matching the blueprint's requirement that alerts be explainable and
    never auto-accusatory. These flag things for a human to look at; none
    of them block or reverse anything on their own.
    """
    alerts: list[dict] = []

    # CRITICAL: budget exceeded
    for budget in Budget.objects.filter(school=school).select_related("department", "term"):
        report = budget_status(budget=budget)
        if report["is_over_budget"]:
            alerts.append(
                {
                    "severity": "critical",
                    "category": "budget_exceeded",
                    "message": (
                        f"{report['department']} has spent {report['spent_amount']} against a "
                        f"{report['allocated_amount']} budget for {report['term']} "
                        f"({report['utilization_pct']}% utilized)."
                    ),
                }
            )

    # CRITICAL: invoice mismatch (procurement discrepancies)
    for po in PurchaseOrder.objects.filter(school=school, supplier_invoice__isnull=False).select_related(
        "purchase_request", "supplier"
    ):
        report = discrepancy_report(purchase_order=po)
        for flag in report["flags"]:
            alerts.append({"severity": "critical", "category": "invoice_mismatch", "message": f"PO-{po.id} ({po.supplier.name}): {flag}"})

    # CRITICAL: duplicate payment detected -- same invoice + amount + method,
    # completed, recorded within DUPLICATE_PAYMENT_WINDOW_HOURS of each other.
    payments = list(
        Payment.objects.filter(school=school, status="completed")
        .order_by("invoice_id", "amount", "method", "paid_at")
    )
    for (invoice_id, amount, method), group in groupby(payments, key=lambda p: (p.invoice_id, p.amount, p.method)):
        group_list = list(group)
        if len(group_list) < 2:
            continue
        for earlier, later in zip(group_list, group_list[1:]):
            gap_hours = (later.paid_at - earlier.paid_at).total_seconds() / 3600
            if gap_hours <= DUPLICATE_PAYMENT_WINDOW_HOURS:
                alerts.append(
                    {
                        "severity": "critical",
                        "category": "duplicate_payment",
                        "message": (
                            f"Two {method} payments of {amount} recorded against invoice #{invoice_id} "
                            f"within {gap_hours:.1f} hours of each other -- review for duplication."
                        ),
                    }
                )

    # WARNING: expenses awaiting approval
    pending_count = Expense.objects.filter(school=school, status="pending_approval").count()
    if pending_count > 0:
        alerts.append(
            {"severity": "warning", "category": "pending_approvals", "message": f"{pending_count} expense request(s) awaiting approval."}
        )

    # WARNING: overdue invoices (term has ended, invoice still not fully paid)
    today = date.today()
    overdue = Invoice.objects.filter(school=school, term__end_date__lt=today).exclude(status__in=["paid", "cancelled"])
    for invoice in overdue.select_related("student", "term"):
        alerts.append(
            {
                "severity": "warning",
                "category": "overdue_invoice",
                "message": f"Invoice #{invoice.id} for {invoice.student.full_name} ({invoice.term.name}) has an outstanding balance of {invoice.balance}.",
            }
        )

    return alerts
