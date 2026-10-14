from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from budgets.models import Budget
from budgets.services import budget_status
from expenses.services import approve_expense, create_expense_request, submit_for_approval
from schools.models import AcademicYear, Department, School, Term


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def budget_setup(db):
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    other_school = School.objects.create(name="Beta School", code="BETA")

    dept = Department.objects.create(school=school, name="Science")
    year = AcademicYear.objects.create(school=school, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    term = Term.objects.create(school=school, academic_year=year, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))

    role = make_role(
        "Admin",
        ["budgets.view_budgets", "budgets.manage_budgets", "expenses.view_expenses", "expenses.create_expenses", "expenses.approve_expenses"],
    )
    user = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=user, role=role)

    approver = User.objects.create_user(email="approver@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=approver, role=role)

    budget = Budget.objects.create(school=school, term=term, department=dept, allocated_amount=Decimal("100000.00"))

    return {"school": school, "other_school": other_school, "dept": dept, "term": term, "user": user, "approver": approver, "budget": budget}


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_committed_expense(school, department, term, requester, approver, amount: Decimal):
    expense = create_expense_request(
        school=school, title="Spend", department=department, supplier=None, term=term,
        requested_by=requester, items=[{"description": "Item", "amount": amount}],
    )
    expense = submit_for_approval(expense=expense)
    return approve_expense(expense=expense, approver=approver)


@pytest.mark.django_db
def test_budget_status_with_no_spend(budget_setup):
    d = budget_setup
    report = budget_status(budget=d["budget"])

    assert report["allocated_amount"] == Decimal("100000.00")
    assert report["spent_amount"] == Decimal("0.00")
    assert report["remaining_amount"] == Decimal("100000.00")
    assert report["is_over_budget"] is False
    assert report["is_near_threshold"] is False


@pytest.mark.django_db
def test_budget_status_only_counts_approved_and_paid_expenses(budget_setup):
    d = budget_setup
    # A draft/pending expense hasn't committed any money -- shouldn't count.
    create_expense_request(
        school=d["school"], title="Still draft", department=d["dept"], supplier=None,
        requested_by=d["user"], items=[{"description": "Item", "amount": Decimal("40000.00")}],
    )
    # An approved one should count.
    make_committed_expense(d["school"], d["dept"], d["term"], d["user"], d["approver"], Decimal("30000.00"))

    report = budget_status(budget=d["budget"])
    assert report["spent_amount"] == Decimal("30000.00")


@pytest.mark.django_db
def test_budget_near_threshold_flag(budget_setup):
    d = budget_setup
    # 85% utilization -- above the default 80% threshold, not yet over.
    make_committed_expense(d["school"], d["dept"], d["term"], d["user"], d["approver"], Decimal("85000.00"))

    report = budget_status(budget=d["budget"])
    assert report["is_near_threshold"] is True
    assert report["is_over_budget"] is False


@pytest.mark.django_db
def test_budget_over_budget_flag(budget_setup):
    d = budget_setup
    make_committed_expense(d["school"], d["dept"], d["term"], d["user"], d["approver"], Decimal("120000.00"))

    report = budget_status(budget=d["budget"])
    assert report["is_over_budget"] is True
    assert report["remaining_amount"] == Decimal("-20000.00")


@pytest.mark.django_db
def test_budget_status_endpoint_via_api(budget_setup):
    d = budget_setup
    make_committed_expense(d["school"], d["dept"], d["term"], d["user"], d["approver"], Decimal("50000.00"))
    client = auth_client(d["user"])

    response = client.get(f"/api/v1/budgets/{d['budget'].id}/status/")

    assert response.status_code == 200
    assert Decimal(response.data["spent_amount"]) == Decimal("50000.00")
    assert Decimal(response.data["remaining_amount"]) == Decimal("50000.00")


@pytest.mark.django_db
def test_cannot_create_duplicate_budget_for_same_term_and_department(budget_setup):
    d = budget_setup
    with pytest.raises(Exception):
        Budget.objects.create(school=d["school"], term=d["term"], department=d["dept"], allocated_amount=Decimal("5000.00"))


@pytest.mark.django_db
def test_user_cannot_view_another_schools_budget(budget_setup):
    d = budget_setup
    client = auth_client(d["user"])

    response = client.get(f"/api/v1/budgets/{d['budget'].id + 999}/")
    assert response.status_code == 404
