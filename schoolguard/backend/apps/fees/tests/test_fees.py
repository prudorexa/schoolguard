from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from fees.models import FeeCategory, Invoice, Payment, Receipt
from fees.services import PaymentValidationError, record_payment, reverse_payment
from schools.models import AcademicYear, School, Term
from students.models import Student


def make_role(name: str, codenames: list[str]) -> Role:
    role = Role.objects.create(name=name)
    for codename in codenames:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def fees_setup(db):
    school_a = School.objects.create(name="Alpha Academy", code="ALPHA")
    school_b = School.objects.create(name="Beta School", code="BETA")

    year_a = AcademicYear.objects.create(school=school_a, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    term_a = Term.objects.create(school=school_a, academic_year=year_a, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))

    year_b = AcademicYear.objects.create(school=school_b, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    term_b = Term.objects.create(school=school_b, academic_year=year_b, name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))

    student_a = Student.objects.create(school=school_a, admission_number="A001", first_name="Amina", last_name="Otieno")
    student_b = Student.objects.create(school=school_b, admission_number="B001", first_name="Brian", last_name="Kamau")

    tuition_a = FeeCategory.objects.create(school=school_a, name="Tuition")

    accountant_role = make_role(
        "Accountant",
        ["fees.view_invoices", "fees.manage_invoices", "fees.record_payments"],
    )
    admin_role = make_role(
        "SchoolAdminFull",
        ["fees.view_invoices", "fees.manage_invoices", "fees.record_payments", "fees.reverse_payments"],
    )

    accountant_a = User.objects.create_user(email="accountant@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=accountant_a, role=accountant_role)

    admin_a = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=admin_a, role=admin_role)

    accountant_b = User.objects.create_user(email="accountant@beta.test", password="pass12345", school=school_b)
    UserRole.objects.create(user=accountant_b, role=accountant_role)

    return {
        "school_a": school_a, "school_b": school_b,
        "term_a": term_a, "term_b": term_b,
        "student_a": student_a, "student_b": student_b,
        "tuition_a": tuition_a,
        "accountant_a": accountant_a, "admin_a": admin_a, "accountant_b": accountant_b,
    }


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_invoice_total_is_computed_from_line_items_not_client_input(fees_setup):
    d = fees_setup
    client = auth_client(d["accountant_a"])

    response = client.post(
        "/api/v1/invoices/",
        {
            "student": d["student_a"].id,
            "term": d["term_a"].id,
            "items": [
                {"fee_category_id": d["tuition_a"].id, "amount": "15000.00", "description": "Tuition"},
                {"fee_category_id": d["tuition_a"].id, "amount": "2500.50", "description": "Activity fee"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert Decimal(response.data["total_amount"]) == Decimal("17500.50")
    assert response.data["status"] == "issued"
    assert response.data["balance"] == "17500.50"


@pytest.mark.django_db
def test_payment_reduces_balance_and_generates_receipt(fees_setup):
    d = fees_setup
    client = auth_client(d["accountant_a"])
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("10000.00"))

    response = client.post(
        "/api/v1/payments/",
        {"invoice": invoice.id, "amount": "4000.00", "method": "mpesa", "reference_number": "QK123"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["receipt_number"] is not None
    assert Receipt.objects.filter(payment_id=response.data["id"]).exists()

    invoice.refresh_from_db()
    assert invoice.balance == Decimal("6000.00")
    assert invoice.status == "partially_paid"


@pytest.mark.django_db
def test_full_payment_marks_invoice_paid(fees_setup):
    d = fees_setup
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("5000.00"))

    record_payment(
        school=d["school_a"], invoice=invoice, amount=Decimal("5000.00"),
        method="cash", reference_number="", recorded_by=d["accountant_a"],
    )

    invoice.refresh_from_db()
    assert invoice.status == "paid"
    assert invoice.balance == Decimal("0.00")


@pytest.mark.django_db
def test_overpayment_is_rejected(fees_setup):
    d = fees_setup
    client = auth_client(d["accountant_a"])
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("1000.00"))

    response = client.post(
        "/api/v1/payments/",
        {"invoice": invoice.id, "amount": "1500.00", "method": "cash", "reference_number": ""},
        format="json",
    )

    assert response.status_code == 400
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("0.00")
    assert invoice.status == "issued"


@pytest.mark.django_db
def test_payment_reversal_restores_balance_and_never_deletes_the_payment(fees_setup):
    d = fees_setup
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("3000.00"))
    payment = record_payment(
        school=d["school_a"], invoice=invoice, amount=Decimal("3000.00"),
        method="bank_transfer", reference_number="TXN1", recorded_by=d["accountant_a"],
    )
    invoice.refresh_from_db()
    assert invoice.status == "paid"

    reverse_payment(payment=payment, reason="Duplicate entry, wrong invoice", actor=d["accountant_a"])

    payment.refresh_from_db()
    invoice.refresh_from_db()
    assert payment.status == "reversed"
    assert Payment.objects.filter(id=payment.id).exists()  # never deleted
    assert invoice.status == "issued"
    assert invoice.balance == Decimal("3000.00")


@pytest.mark.django_db
def test_reversal_without_reason_is_rejected(fees_setup):
    d = fees_setup
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("1000.00"))
    payment = record_payment(
        school=d["school_a"], invoice=invoice, amount=Decimal("1000.00"),
        method="cash", reference_number="", recorded_by=d["accountant_a"],
    )

    with pytest.raises(PaymentValidationError):
        reverse_payment(payment=payment, reason="   ", actor=d["accountant_a"])


@pytest.mark.django_db
def test_accountant_cannot_reverse_own_recorded_payment_via_api(fees_setup):
    """Separation of duties: recording != reversing. The Accountant role
    here deliberately lacks fees.reverse_payments."""
    d = fees_setup
    client = auth_client(d["accountant_a"])
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("1000.00"))
    payment = record_payment(
        school=d["school_a"], invoice=invoice, amount=Decimal("1000.00"),
        method="cash", reference_number="", recorded_by=d["accountant_a"],
    )

    response = client.post(f"/api/v1/payments/{payment.id}/reverse/", {"reason": "test"}, format="json")

    assert response.status_code == 403
    payment.refresh_from_db()
    assert payment.status == "completed"


@pytest.mark.django_db
def test_admin_with_reverse_permission_can_reverse(fees_setup):
    d = fees_setup
    client = auth_client(d["admin_a"])
    invoice = Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("1000.00"))
    payment = record_payment(
        school=d["school_a"], invoice=invoice, amount=Decimal("1000.00"),
        method="cash", reference_number="", recorded_by=d["accountant_a"],
    )

    response = client.post(f"/api/v1/payments/{payment.id}/reverse/", {"reason": "Wrong student"}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "reversed"


@pytest.mark.django_db
def test_cannot_pay_another_schools_invoice(fees_setup):
    d = fees_setup
    client = auth_client(d["accountant_a"])
    invoice_b = Invoice.objects.create(school=d["school_b"], student=d["student_b"], term=d["term_b"], total_amount=Decimal("1000.00"))

    response = client.post(
        "/api/v1/payments/",
        {"invoice": invoice_b.id, "amount": "500.00", "method": "cash", "reference_number": ""},
        format="json",
    )

    # invoice_b isn't in accountant_a's tenant-scoped queryset at all --
    # structurally invisible, same as the Department/Student isolation tests.
    assert response.status_code == 404
    invoice_b.refresh_from_db()
    assert invoice_b.amount_paid == Decimal("0.00")


@pytest.mark.django_db
def test_user_only_sees_own_schools_invoices_in_list(fees_setup):
    d = fees_setup
    Invoice.objects.create(school=d["school_a"], student=d["student_a"], term=d["term_a"], total_amount=Decimal("1000.00"))
    Invoice.objects.create(school=d["school_b"], student=d["student_b"], term=d["term_b"], total_amount=Decimal("2000.00"))

    client = auth_client(d["accountant_a"])
    response = client.get("/api/v1/invoices/")

    assert response.status_code == 200
    assert all(row["student"] == d["student_a"].id for row in response.data["results"])
