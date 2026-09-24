from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from budgets.models import Budget
from dashboard.services import financial_alerts, financial_summary
from expenses.services import approve_expense, create_expense_request, submit_for_approval
from fees.models import Invoice, Payment
from fees.services import record_payment
from schools.models import AcademicYear, Department, School, Term
from students.models import Student


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def dashboard_setup(db):
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    dept = Department.objects.create(school=school, name="Science")
    today = date.today()
    year = AcademicYear.objects.create(school=school, name="Current Year", start_date=today - timedelta(days=180), end_date=today + timedelta(days=180))
    term = Term.objects.create(
        school=school, academic_year=year, name="Current Term",
        start_date=today - timedelta(days=30), end_date=today + timedelta(days=60),
    )
    student = Student.objects.create(school=school, admission_number="A001", first_name="Amina", last_name="Otieno")

    role = make_role(
        "Full",
        [
            "fees.view_invoices", "fees.manage_invoices", "fees.record_payments",
            "expenses.view_expenses", "expenses.create_expenses", "expenses.approve_expenses",
            "budgets.view_budgets", "budgets.manage_budgets", "dashboard.view_dashboard",
        ],
    )
    user = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=user, role=role)

    approver = User.objects.create_user(email="approver@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=approver, role=role)

    no_dashboard_role = make_role("Limited", ["fees.view_invoices"])
    limited_user = User.objects.create_user(email="limited@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=limited_user, role=no_dashboard_role)

    return {"school": school, "dept": dept, "term": term, "student": student, "user": user, "approver": approver, "limited_user": limited_user}


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_summary_reflects_real_payments_and_expenses(dashboard_setup):
    d = dashboard_setup
    invoice = Invoice.objects.create(school=d["school"], student=d["student"], term=d["term"], total_amount=Decimal("10000.00"))
    record_payment(school=d["school"], invoice=invoice, amount=Decimal("6000.00"), method="cash", reference_number="", recorded_by=d["user"])

    expense = create_expense_request(
        school=d["school"], title="Supplies", department=d["dept"], supplier=None, term=d["term"],
        requested_by=d["user"], items=[{"description": "Paper", "amount": Decimal("1000.00")}],
    )
    expense = submit_for_approval(expense=expense)
    expense = approve_expense(expense=expense, approver=d["approver"])
    from expenses.services import mark_expense_paid
    mark_expense_paid(expense=expense, actor=d["user"])

    summary = financial_summary(school=d["school"])

    assert summary["total_collected"] == Decimal("6000.00")
    assert summary["total_expenses"] == Decimal("1000.00")
    assert summary["outstanding_fees"] == Decimal("4000.00")
    assert summary["net_position"] == Decimal("5000.00")


@pytest.mark.django_db
def test_summary_endpoint_requires_permission(dashboard_setup):
    d = dashboard_setup
    client = auth_client(d["limited_user"])

    response = client.get("/api/v1/dashboard/summary/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_summary_endpoint_works_for_permitted_user(dashboard_setup):
    d = dashboard_setup
    client = auth_client(d["user"])

    response = client.get("/api/v1/dashboard/summary/")

    assert response.status_code == 200
    assert "total_collected" in response.data


@pytest.mark.django_db
def test_budget_exceeded_alert_fires(dashboard_setup):
    d = dashboard_setup
    Budget.objects.create(school=d["school"], term=d["term"], department=d["dept"], allocated_amount=Decimal("1000.00"))
    expense = create_expense_request(
        school=d["school"], title="Overspend", department=d["dept"], supplier=None, term=d["term"],
        requested_by=d["user"], items=[{"description": "Item", "amount": Decimal("1500.00")}],
    )
    expense = submit_for_approval(expense=expense)
    approve_expense(expense=expense, approver=d["approver"])

    alerts = financial_alerts(school=d["school"])

    categories = [a["category"] for a in alerts]
    assert "budget_exceeded" in categories
    matching = [a for a in alerts if a["category"] == "budget_exceeded"][0]
    assert matching["severity"] == "critical"


@pytest.mark.django_db
def test_pending_approval_alert_fires(dashboard_setup):
    d = dashboard_setup
    expense = create_expense_request(
        school=d["school"], title="Needs approval", department=d["dept"], supplier=None, term=d["term"],
        requested_by=d["user"], items=[{"description": "Item", "amount": Decimal("500.00")}],
    )
    submit_for_approval(expense=expense)

    alerts = financial_alerts(school=d["school"])

    matching = [a for a in alerts if a["category"] == "pending_approvals"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"
    assert "1 expense request" in matching[0]["message"]


@pytest.mark.django_db
def test_overdue_invoice_alert_fires_after_term_ends(dashboard_setup):
    d = dashboard_setup
    past_year = AcademicYear.objects.create(school=d["school"], name="2020", start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
    past_term = Term.objects.create(school=d["school"], academic_year=past_year, name="Old Term", start_date=date(2020, 1, 1), end_date=date(2020, 4, 1))
    Invoice.objects.create(school=d["school"], student=d["student"], term=past_term, total_amount=Decimal("2000.00"))

    alerts = financial_alerts(school=d["school"])

    matching = [a for a in alerts if a["category"] == "overdue_invoice"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"


@pytest.mark.django_db
def test_no_overdue_alert_for_current_term_invoice(dashboard_setup):
    d = dashboard_setup
    Invoice.objects.create(school=d["school"], student=d["student"], term=d["term"], total_amount=Decimal("2000.00"))

    alerts = financial_alerts(school=d["school"])

    assert not [a for a in alerts if a["category"] == "overdue_invoice"]


@pytest.mark.django_db
def test_duplicate_payment_alert_fires_for_same_invoice_amount_method_within_window(dashboard_setup):
    d = dashboard_setup
    invoice = Invoice.objects.create(school=d["school"], student=d["student"], term=d["term"], total_amount=Decimal("20000.00"))

    p1 = record_payment(school=d["school"], invoice=invoice, amount=Decimal("5000.00"), method="mpesa", reference_number="QK1", recorded_by=d["user"])
    p2 = record_payment(school=d["school"], invoice=invoice, amount=Decimal("5000.00"), method="mpesa", reference_number="QK2", recorded_by=d["user"])

    # Force them to look like they happened close together (record_payment
    # uses auto_now_add, so we adjust after the fact to simulate the
    # "recorded twice within an hour" scenario deterministically).
    Payment.objects.filter(id=p1.id).update(paid_at=timezone.now())
    Payment.objects.filter(id=p2.id).update(paid_at=timezone.now() + timedelta(minutes=10))

    alerts = financial_alerts(school=d["school"])

    matching = [a for a in alerts if a["category"] == "duplicate_payment"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "critical"


@pytest.mark.django_db
def test_no_duplicate_alert_for_payments_far_apart(dashboard_setup):
    d = dashboard_setup
    invoice = Invoice.objects.create(school=d["school"], student=d["student"], term=d["term"], total_amount=Decimal("20000.00"))

    p1 = record_payment(school=d["school"], invoice=invoice, amount=Decimal("5000.00"), method="mpesa", reference_number="QK1", recorded_by=d["user"])
    p2 = record_payment(school=d["school"], invoice=invoice, amount=Decimal("5000.00"), method="mpesa", reference_number="QK2", recorded_by=d["user"])

    Payment.objects.filter(id=p1.id).update(paid_at=timezone.now())
    Payment.objects.filter(id=p2.id).update(paid_at=timezone.now() + timedelta(days=10))

    alerts = financial_alerts(school=d["school"])

    assert not [a for a in alerts if a["category"] == "duplicate_payment"]


@pytest.mark.django_db
def test_alerts_are_scoped_to_school(dashboard_setup):
    d = dashboard_setup
    other_school = School.objects.create(name="Beta School", code="BETA")
    other_dept = Department.objects.create(school=other_school, name="Finance")
    other_year = AcademicYear.objects.create(school=other_school, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    other_term = Term.objects.create(school=other_school, academic_year=other_year, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))
    Budget.objects.create(school=other_school, term=other_term, department=other_dept, allocated_amount=Decimal("100.00"))
    other_user = User.objects.create_user(email="other@beta.test", password="pass12345", school=other_school)
    other_approver = User.objects.create_user(email="other_approver@beta.test", password="pass12345", school=other_school)
    expense = create_expense_request(
        school=other_school, title="Other school overspend", department=other_dept, supplier=None, term=other_term,
        requested_by=other_user, items=[{"description": "Item", "amount": Decimal("500.00")}],
    )
    expense = submit_for_approval(expense=expense)
    approve_expense(expense=expense, approver=other_approver)

    alerts = financial_alerts(school=d["school"])

    assert not [a for a in alerts if "Finance" in a["message"]]
