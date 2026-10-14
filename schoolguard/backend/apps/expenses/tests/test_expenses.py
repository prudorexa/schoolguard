from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from expenses.models import Expense
from expenses.services import (
    ExpenseWorkflowError,
    approve_expense,
    create_expense_request,
    mark_expense_paid,
    reject_expense,
    submit_for_approval,
)
from schools.models import Department, School
from suppliers.models import Supplier


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def expenses_setup(db):
    school_a = School.objects.create(name="Alpha Academy", code="ALPHA")
    school_b = School.objects.create(name="Beta School", code="BETA")

    dept_a = Department.objects.create(school=school_a, name="Science")
    dept_b = Department.objects.create(school=school_b, name="Finance")

    supplier_a = Supplier.objects.create(school=school_a, name="ABC Supplies")

    dept_head_role = make_role("Dept Head", ["expenses.view_expenses", "expenses.create_expenses"])
    principal_role = make_role("Principal", ["expenses.view_expenses", "expenses.approve_expenses"])
    accountant_role = make_role(
        "Accountant", ["expenses.view_expenses", "expenses.create_expenses", "expenses.record_expense_payment"]
    )

    dept_head_a = User.objects.create_user(email="depthead@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=dept_head_a, role=dept_head_role)

    principal_a = User.objects.create_user(email="principal@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=principal_a, role=principal_role)

    accountant_a = User.objects.create_user(email="accountant@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=accountant_a, role=accountant_role)

    # Also give the Principal the create permission, so we can test
    # self-approval blocking a Principal's *own* request too.
    RolePermission.objects.get_or_create(
        role=principal_role, permission=Permission.objects.get(codename="expenses.create_expenses")
    )

    dept_head_b = User.objects.create_user(email="depthead@beta.test", password="pass12345", school=school_b)
    UserRole.objects.create(user=dept_head_b, role=dept_head_role)

    return {
        "school_a": school_a, "school_b": school_b,
        "dept_a": dept_a, "dept_b": dept_b, "supplier_a": supplier_a,
        "dept_head_a": dept_head_a, "principal_a": principal_a, "accountant_a": accountant_a,
        "dept_head_b": dept_head_b,
    }


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_pending_expense(school, department, requester) -> Expense:
    expense = create_expense_request(
        school=school, title="Lab equipment", department=department, supplier=None,
        requested_by=requester, items=[{"description": "Microscopes", "amount": Decimal("50000.00")}],
    )
    return submit_for_approval(expense=expense)


@pytest.mark.django_db
def test_expense_amount_computed_from_line_items(expenses_setup):
    d = expenses_setup
    client = auth_client(d["dept_head_a"])

    response = client.post(
        "/api/v1/expenses/",
        {
            "title": "Lab equipment",
            "department": d["dept_a"].id,
            "supplier": d["supplier_a"].id,
            "items": [
                {"description": "Microscopes", "amount": "50000.00"},
                {"description": "Beakers", "amount": "3500.00"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert Decimal(response.data["amount"]) == Decimal("53500.00")
    assert response.data["status"] == "draft"


@pytest.mark.django_db
def test_full_happy_path_draft_to_paid(expenses_setup):
    d = expenses_setup
    expense = create_expense_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], supplier=None,
        requested_by=d["dept_head_a"], items=[{"description": "Microscopes", "amount": Decimal("50000.00")}],
    )
    assert expense.status == "draft"

    expense = submit_for_approval(expense=expense)
    assert expense.status == "pending_approval"

    expense = approve_expense(expense=expense, approver=d["principal_a"])
    assert expense.status == "approved"
    assert expense.approved_by_id == d["principal_a"].id

    expense = mark_expense_paid(expense=expense, actor=d["principal_a"])
    assert expense.status == "paid"
    assert expense.paid_at is not None


@pytest.mark.django_db
def test_requester_cannot_approve_own_expense(expenses_setup):
    """The rule that matters most in this module: enforced in the service
    layer, independent of the approver's permissions -- even if the
    requester happens to also hold expenses.approve_expenses."""
    d = expenses_setup
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["principal_a"])  # Principal requests...

    with pytest.raises(ExpenseWorkflowError, match="cannot approve your own"):
        approve_expense(expense=expense, approver=d["principal_a"])  # ...and tries to approve it themselves

    expense.refresh_from_db()
    assert expense.status == "pending_approval"


@pytest.mark.django_db
def test_requester_cannot_reject_own_expense(expenses_setup):
    d = expenses_setup
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["principal_a"])

    with pytest.raises(ExpenseWorkflowError, match="cannot reject your own"):
        reject_expense(expense=expense, approver=d["principal_a"], reason="changed my mind")

    expense.refresh_from_db()
    assert expense.status == "pending_approval"


@pytest.mark.django_db
def test_self_approval_blocked_via_api_too(expenses_setup):
    d = expenses_setup
    client = auth_client(d["principal_a"])
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["principal_a"])

    response = client.post(f"/api/v1/expenses/{expense.id}/approve/", format="json")

    assert response.status_code == 400
    expense.refresh_from_db()
    assert expense.status == "pending_approval"


@pytest.mark.django_db
def test_different_approver_succeeds(expenses_setup):
    d = expenses_setup
    client = auth_client(d["principal_a"])
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["dept_head_a"])

    response = client.post(f"/api/v1/expenses/{expense.id}/approve/", format="json")

    assert response.status_code == 200
    assert response.data["status"] == "approved"


@pytest.mark.django_db
def test_cannot_skip_straight_from_draft_to_paid(expenses_setup):
    d = expenses_setup
    expense = create_expense_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], supplier=None,
        requested_by=d["dept_head_a"], items=[{"description": "Microscopes", "amount": Decimal("50000.00")}],
    )
    assert expense.status == "draft"

    with pytest.raises(ExpenseWorkflowError):
        mark_expense_paid(expense=expense, actor=d["dept_head_a"])


@pytest.mark.django_db
def test_department_head_cannot_approve_expenses(expenses_setup):
    """Separation of duties: the requester role doesn't hold
    expenses.approve_expenses at all in the seed data."""
    d = expenses_setup
    client = auth_client(d["dept_head_a"])
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["dept_head_a"])

    response = client.post(f"/api/v1/expenses/{expense.id}/approve/", format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_accountant_can_mark_paid_but_not_approve(expenses_setup):
    d = expenses_setup
    expense = make_pending_expense(d["school_a"], d["dept_a"], d["dept_head_a"])
    expense = approve_expense(expense=expense, approver=d["principal_a"])

    client = auth_client(d["accountant_a"])

    approve_attempt = client.post(f"/api/v1/expenses/{expense.id}/approve/", format="json")
    assert approve_attempt.status_code in (403, 400)  # 403 lacks perm; irrelevant here since already approved, but must not be 200

    pay_attempt = client.post(f"/api/v1/expenses/{expense.id}/mark-paid/", format="json")
    assert pay_attempt.status_code == 200
    assert pay_attempt.data["status"] == "paid"


@pytest.mark.django_db
def test_approver_without_create_permission_can_still_approve(expenses_setup):
    """Regression test: a role holding ONLY expenses.approve_expenses (not
    expenses.create_expenses) must still be able to approve. This is
    exactly the real seed_rbac.py shape for Principal, and was broken by an
    earlier version of this view where the class-level permission check
    (tied to create_expenses) incorrectly gated the approve action too."""
    d = expenses_setup
    approver_only_role = make_role("ApproveOnly", ["expenses.view_expenses", "expenses.approve_expenses"])
    approver = User.objects.create_user(email="approveonly@alpha.test", password="pass12345", school=d["school_a"])
    UserRole.objects.create(user=approver, role=approver_only_role)

    expense = make_pending_expense(d["school_a"], d["dept_a"], d["dept_head_a"])
    client = auth_client(approver)

    response = client.post(f"/api/v1/expenses/{expense.id}/approve/", format="json")

    assert response.status_code == 200
    assert response.data["status"] == "approved"


@pytest.mark.django_db
def test_user_cannot_see_or_approve_another_schools_expense(expenses_setup):
    d = expenses_setup
    expense_b = make_pending_expense(d["school_b"], d["dept_b"], d["dept_head_b"])

    client = auth_client(d["principal_a"])
    response = client.post(f"/api/v1/expenses/{expense_b.id}/approve/", format="json")

    assert response.status_code == 404
    expense_b.refresh_from_db()
    assert expense_b.status == "pending_approval"
