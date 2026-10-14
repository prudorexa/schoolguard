"""
Tests use a FakeClaudeClient instead of the real anthropic.Anthropic()
client, since this sandbox's network policy doesn't include
api.anthropic.com. What's actually under test here -- and what matters
most for correctness -- is entirely on our side of that boundary: which
tool gets executed, that it's scoped to the caller's own school, that the
data handed back to Claude for the final answer is the real computed data
(not invented), and that every call is logged. The real API call itself
(request/response wire format against the live service) is implemented
correctly per the SDK's documented interface but has not been exercised
end-to-end in this environment -- worth a person verifying with a real
ANTHROPIC_API_KEY before relying on it in production.
"""

from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from ai.claude_client import AIConfigurationError
from ai.models import AIAnalysisRecord
from ai.services import AIAssistantError, ask_assistant
from budgets.models import Budget
from expenses.services import approve_expense, create_expense_request, submit_for_approval
from schools.models import AcademicYear, Department, School, Term


@dataclass
class FakeToolUseBlock:
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list


@dataclass
class FakeMessages:
    """Records every call it receives so tests can assert on what was
    actually sent to 'Claude' -- particularly that the grounding call
    includes the real tool data, not something invented."""

    responses: list
    calls: list = field(default_factory=list)
    _index: int = 0

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses[self._index]
        self._index += 1
        return response


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def ai_setup(db):
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    dept = Department.objects.create(school=school, name="Science")
    year = AcademicYear.objects.create(school=school, name="2026", start_date="2026-01-01", end_date="2026-12-31")
    term = Term.objects.create(school=school, academic_year=year, name="Term 1", start_date="2026-01-01", end_date="2026-04-01")
    Budget.objects.create(school=school, term=term, department=dept, allocated_amount=Decimal("100000.00"))

    role = make_role("Full", ["ai.use_assistant", "expenses.view_expenses", "expenses.create_expenses", "expenses.approve_expenses"])
    user = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=user, role=role)

    no_ai_role = make_role("NoAI", ["expenses.view_expenses"])
    limited_user = User.objects.create_user(email="limited@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=limited_user, role=no_ai_role)

    return {"school": school, "dept": dept, "term": term, "user": user, "limited_user": limited_user}


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_ask_assistant_executes_the_tool_claude_selects_and_logs_it(ai_setup):
    d = ai_setup
    fake = FakeClient(
        responses=[
            FakeResponse(content=[FakeToolUseBlock(name="get_budget_status", input={"department_name": "Science", "term_name": "Term 1"})]),
            FakeResponse(content=[FakeTextBlock(text="Science has spent 0 of its 100000 budget so far.")]),
        ]
    )

    result = ask_assistant(school=d["school"], user=d["user"], question="How is the Science budget doing?", client=fake)

    assert result["tool_called"] == "get_budget_status"
    assert result["data"]["allocated_amount"] == "100000.00"
    assert "Science" in result["answer"]

    record = AIAnalysisRecord.objects.get(school=d["school"])
    assert record.tool_called == "get_budget_status"
    assert record.data_retrieved["allocated_amount"] == "100000.00"
    assert record.answer == result["answer"]
    assert record.error == ""


@pytest.mark.django_db
def test_final_answer_call_is_grounded_in_the_real_tool_data_not_invented(ai_setup):
    """Confirms the second Claude call actually receives the real computed
    data as its input -- the grounding the blueprint requires, not just
    that some number happens to appear in the mocked final answer."""
    d = ai_setup
    fake = FakeClient(
        responses=[
            FakeResponse(content=[FakeToolUseBlock(name="get_budget_status", input={"department_name": "Science", "term_name": "Term 1"})]),
            FakeResponse(content=[FakeTextBlock(text="...")]),
        ]
    )

    ask_assistant(school=d["school"], user=d["user"], question="How is the Science budget doing?", client=fake)

    grounding_call = fake.messages.calls[1]
    assert "100000.00" in grounding_call["messages"][0]["content"]
    assert "Only use the numbers given" in grounding_call["system"] or "ONLY" in grounding_call["system"]


@pytest.mark.django_db
def test_budget_status_tool_is_scoped_to_callers_own_school(ai_setup):
    d = ai_setup
    other_school = School.objects.create(name="Beta School", code="BETA")
    other_dept = Department.objects.create(school=other_school, name="Science")  # same name, different school
    other_year = AcademicYear.objects.create(school=other_school, name="2026", start_date="2026-01-01", end_date="2026-12-31")
    other_term = Term.objects.create(school=other_school, academic_year=other_year, name="Term 1", start_date="2026-01-01", end_date="2026-04-01")
    Budget.objects.create(school=other_school, term=other_term, department=other_dept, allocated_amount=Decimal("999999.00"))

    fake = FakeClient(
        responses=[
            FakeResponse(content=[FakeToolUseBlock(name="get_budget_status", input={"department_name": "Science", "term_name": "Term 1"})]),
            FakeResponse(content=[FakeTextBlock(text="...")]),
        ]
    )

    result = ask_assistant(school=d["school"], user=d["user"], question="Science budget?", client=fake)

    # Must return Alpha's 100000 budget, never Beta's 999999 one, even
    # though both schools have a department literally named "Science".
    assert result["data"]["allocated_amount"] == "100000.00"


@pytest.mark.django_db
def test_budget_status_tool_handles_no_matching_budget_gracefully(ai_setup):
    d = ai_setup
    fake = FakeClient(
        responses=[
            FakeResponse(content=[FakeToolUseBlock(name="get_budget_status", input={"department_name": "Nonexistent", "term_name": "Term 1"})]),
            FakeResponse(content=[FakeTextBlock(text="No budget was found for that department.")]),
        ]
    )

    result = ask_assistant(school=d["school"], user=d["user"], question="Nonexistent dept budget?", client=fake)

    assert "error" in result["data"]


@pytest.mark.django_db
def test_top_expenses_tool_only_includes_committed_expenses(ai_setup):
    d = ai_setup
    # Draft expense -- should never appear, it hasn't committed any money.
    create_expense_request(
        school=d["school"], title="Still draft", department=d["dept"], supplier=None, term=d["term"],
        requested_by=d["user"], items=[{"description": "Item", "amount": Decimal("99999.00")}],
    )
    # Approved expense -- should appear.
    committed = create_expense_request(
        school=d["school"], title="Approved gear", department=d["dept"], supplier=None, term=d["term"],
        requested_by=d["user"], items=[{"description": "Item", "amount": Decimal("5000.00")}],
    )
    committed = submit_for_approval(expense=committed)
    approve_expense(expense=committed, approver=d["limited_user"])  # different approver, self-approval block respected

    fake = FakeClient(
        responses=[
            FakeResponse(content=[FakeToolUseBlock(name="get_top_expenses", input={"limit": 5})]),
            FakeResponse(content=[FakeTextBlock(text="...")]),
        ]
    )

    result = ask_assistant(school=d["school"], user=d["user"], question="Biggest expenses?", client=fake)

    titles = [e["title"] for e in result["data"]["expenses"]]
    assert "Approved gear" in titles
    assert "Still draft" not in titles


@pytest.mark.django_db
def test_missing_api_key_raises_configuration_error_and_is_logged(ai_setup, settings):
    d = ai_setup
    settings.ANTHROPIC_API_KEY = ""

    with pytest.raises(AIConfigurationError):
        ask_assistant(school=d["school"], user=d["user"], question="Anything?", client=None)

    record = AIAnalysisRecord.objects.get(school=d["school"])
    assert "ANTHROPIC_API_KEY" in record.error


@pytest.mark.django_db
def test_no_tool_selected_raises_and_is_logged(ai_setup):
    d = ai_setup
    fake = FakeClient(responses=[FakeResponse(content=[FakeTextBlock(text="I'm not sure how to look that up.")])])

    with pytest.raises(AIAssistantError):
        ask_assistant(school=d["school"], user=d["user"], question="???", client=fake)

    record = AIAnalysisRecord.objects.get(school=d["school"])
    assert record.error != ""
    assert record.tool_called == ""


@pytest.mark.django_db
def test_endpoint_requires_permission(ai_setup):
    d = ai_setup
    client = auth_client(d["limited_user"])

    response = client.post("/api/v1/ai/ask/", {"question": "How are we doing financially?"}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_endpoint_returns_clean_503_when_not_configured(ai_setup, settings):
    """No API key is set in the test environment -- confirms the endpoint
    fails cleanly (503, readable message) rather than a raw exception,
    which is exactly the scenario anyone running this without an API key
    configured will hit."""
    d = ai_setup
    settings.ANTHROPIC_API_KEY = ""
    client = auth_client(d["user"])

    response = client.post("/api/v1/ai/ask/", {"question": "How are we doing financially?"}, format="json")

    assert response.status_code == 503
