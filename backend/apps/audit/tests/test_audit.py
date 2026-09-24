from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from audit.models import AuditLog
from expenses.services import approve_expense, create_expense_request, submit_for_approval
from fees.models import Invoice
from fees.services import record_payment, reverse_payment
from schools.models import Department, School


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def audit_setup(db):
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    dept = Department.objects.create(school=school, name="Science")

    full_role = make_role(
        "Full",
        [
            "fees.view_invoices", "fees.manage_invoices", "fees.record_payments", "fees.reverse_payments",
            "expenses.view_expenses", "expenses.create_expenses", "expenses.approve_expenses",
            "audit.view_audit_logs",
        ],
    )
    accountant = User.objects.create_user(email="accountant@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=accountant, role=full_role)

    no_audit_role = make_role("NoAudit", ["fees.view_invoices"])
    limited_user = User.objects.create_user(email="limited@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=limited_user, role=no_audit_role)

    return {"school": school, "dept": dept, "accountant": accountant, "limited_user": limited_user}


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_recording_a_payment_creates_an_audit_log_entry(audit_setup):
    d = audit_setup
    from schools.models import AcademicYear, Term
    from students.models import Student
    from datetime import date

    year = AcademicYear.objects.create(school=d["school"], name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    term = Term.objects.create(school=d["school"], academic_year=year, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))
    student = Student.objects.create(school=d["school"], admission_number="A001", first_name="Amina", last_name="Otieno")
    invoice = Invoice.objects.create(school=d["school"], student=student, term=term, total_amount=Decimal("5000.00"))

    payment = record_payment(
        school=d["school"], invoice=invoice, amount=Decimal("5000.00"),
        method="cash", reference_number="", recorded_by=d["accountant"],
    )

    log = AuditLog.objects.get(entity_type="Payment", entity_id=payment.id)
    assert log.action == "payment.recorded"
    assert log.user_id == d["accountant"].id
    assert log.new_value["amount"] == "5000.00"


@pytest.mark.django_db
def test_reversing_a_payment_logs_previous_and_new_status_with_reason(audit_setup):
    d = audit_setup
    from schools.models import AcademicYear, Term
    from students.models import Student
    from datetime import date

    year = AcademicYear.objects.create(school=d["school"], name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    term = Term.objects.create(school=d["school"], academic_year=year, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))
    student = Student.objects.create(school=d["school"], admission_number="A002", first_name="Brian", last_name="Kamau")
    invoice = Invoice.objects.create(school=d["school"], student=student, term=term, total_amount=Decimal("2000.00"))
    payment = record_payment(
        school=d["school"], invoice=invoice, amount=Decimal("2000.00"),
        method="cash", reference_number="", recorded_by=d["accountant"],
    )

    reverse_payment(payment=payment, reason="Wrong invoice", actor=d["accountant"])

    log = AuditLog.objects.get(entity_type="Payment", entity_id=payment.id, action="payment.reversed")
    assert log.reason == "Wrong invoice"
    assert log.previous_value["status"] == "completed"
    assert log.new_value["status"] == "reversed"


@pytest.mark.django_db
def test_expense_approval_creates_audit_entry_with_amount(audit_setup):
    d = audit_setup
    expense = create_expense_request(
        school=d["school"], title="Lab equipment", department=d["dept"], supplier=None,
        requested_by=d["limited_user"], items=[{"description": "Microscopes", "amount": Decimal("15000.00")}],
    )
    expense = submit_for_approval(expense=expense)
    approve_expense(expense=expense, approver=d["accountant"])

    log = AuditLog.objects.get(entity_type="Expense", entity_id=expense.id, action="expense.approved")
    assert log.user_id == d["accountant"].id
    assert log.new_value["amount"] == "15000.00"


@pytest.mark.django_db
def test_audit_log_is_scoped_to_school(audit_setup):
    d = audit_setup
    other_school = School.objects.create(name="Beta School", code="BETA")
    from schools.models import Department as Dept

    other_dept = Dept.objects.create(school=other_school, name="Finance")
    other_user_role = make_role("OtherFull", ["expenses.view_expenses", "expenses.create_expenses", "audit.view_audit_logs"])
    other_user = User.objects.create_user(email="other@beta.test", password="pass12345", school=other_school)
    UserRole.objects.create(user=other_user, role=other_user_role)

    expense = create_expense_request(
        school=other_school, title="Other school expense", department=other_dept, supplier=None,
        requested_by=other_user, items=[{"description": "Something", "amount": Decimal("100.00")}],
    )
    submit_for_approval(expense=expense)
    approve_expense(expense=expense, approver=d["accountant"])  # cross-school approver, allowed at service level for this test

    client = auth_client(d["accountant"])
    response = client.get("/api/v1/audit-logs/")

    entity_ids_visible = {row["entity_id"] for row in response.data["results"] if row["entity_type"] == "Expense"}
    assert expense.id not in entity_ids_visible


@pytest.mark.django_db
def test_user_without_permission_cannot_view_audit_log(audit_setup):
    d = audit_setup
    client = auth_client(d["limited_user"])  # only has fees.view_invoices

    response = client.get("/api/v1/audit-logs/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_audit_log_has_no_write_endpoints(audit_setup):
    """ReadOnlyModelViewSet has no create() handler at all, and the
    permission class fails closed (no write codename is configured on this
    viewset) -- either way, POST is blocked. DRF checks permissions before
    resolving the handler, so this surfaces as 403 rather than 405, but the
    result is the same: there is no way to write to this endpoint."""
    d = audit_setup
    client = auth_client(d["accountant"])

    post_response = client.post("/api/v1/audit-logs/", {"action": "fake"}, format="json")
    assert post_response.status_code == 403
    assert not AuditLog.objects.filter(action="fake").exists()
