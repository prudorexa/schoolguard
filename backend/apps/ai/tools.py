"""
ai/tools.py

The whitelist. Every tool here maps 1:1 to an existing, already-tested
service function from another app (dashboard, budgets, expenses) -- the AI
layer adds NO new data-access logic of its own. Claude picks a tool by
name and supplies parameters; this module is what actually executes it,
against the caller's own `school`, using the exact same function a human
action in the UI would call. There is no code path from here into raw SQL,
the ORM directly, or another school's data.

Decimal amounts are converted to strings before being handed back to
Claude (JSON has no Decimal type, and string avoids float-precision drift
on money figures) -- same approach as audit.services._json_safe.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from budgets.models import Budget
from budgets.services import budget_status
from dashboard.services import financial_alerts, financial_summary
from expenses.models import Expense


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return value


def _tool_financial_summary(school, **_kwargs) -> dict:
    return _json_safe(financial_summary(school=school))


def _tool_financial_alerts(school, **_kwargs) -> dict:
    return {"alerts": _json_safe(financial_alerts(school=school))}


def _tool_budget_status(school, department_name: str, term_name: str, **_kwargs) -> dict:
    budget = (
        Budget.objects.filter(school=school, department__name__iexact=department_name, term__name__iexact=term_name)
        .select_related("department", "term")
        .first()
    )
    if budget is None:
        return {"error": f"No budget found for department '{department_name}' in term '{term_name}'."}
    return _json_safe(budget_status(budget=budget))


def _tool_pending_expense_approvals(school, **_kwargs) -> dict:
    expenses = Expense.objects.filter(school=school, status="pending_approval").select_related("department")[:20]
    return {
        "count": expenses.count(),
        "expenses": [
            {"id": e.id, "title": e.title, "department": e.department.name, "amount": str(e.amount)} for e in expenses
        ],
    }


def _tool_top_expenses(school, limit: int = 5, **_kwargs) -> dict:
    limit = max(1, min(int(limit), 20))
    expenses = (
        Expense.objects.filter(school=school, status__in=["approved", "paid"])
        .select_related("department")
        .order_by("-amount")[:limit]
    )
    return {
        "expenses": [
            {"id": e.id, "title": e.title, "department": e.department.name, "amount": str(e.amount), "status": e.status}
            for e in expenses
        ]
    }


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_financial_summary": {
        "description": "Get overall financial summary: total collected, total expenses, outstanding fees, net position, budget utilization, pending approvals, and recent transactions.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": _tool_financial_summary,
    },
    "get_financial_alerts": {
        "description": "Get the current Financial Control Center alerts: budget overruns, invoice/PO mismatches, duplicate payments, expenses awaiting approval, overdue invoices.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": _tool_financial_alerts,
    },
    "get_budget_status": {
        "description": "Get allocated/spent/remaining/utilization for a specific department's budget in a specific term.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department_name": {"type": "string", "description": "e.g. 'Science'"},
                "term_name": {"type": "string", "description": "e.g. 'Term 1'"},
            },
            "required": ["department_name", "term_name"],
        },
        "handler": _tool_budget_status,
    },
    "get_pending_expense_approvals": {
        "description": "List expense requests currently awaiting approval.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": _tool_pending_expense_approvals,
    },
    "get_top_expenses": {
        "description": "List the largest approved/paid expenses, most expensive first.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "How many to return (max 20)."}},
        },
        "handler": _tool_top_expenses,
    },
}


def build_claude_tools() -> list[dict]:
    """Tool definitions in the shape the Anthropic Messages API expects."""
    return [
        {"name": name, "description": spec["description"], "input_schema": spec["input_schema"]}
        for name, spec in TOOL_REGISTRY.items()
    ]


def execute_tool(name: str, school, params: dict) -> dict:
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {"error": f"Unknown tool: {name}"}
    handler: Callable = spec["handler"]
    return handler(school, **params)
