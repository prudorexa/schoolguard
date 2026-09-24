from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from procurement.models import PurchaseRequest
from procurement.services import (
    ProcurementWorkflowError,
    approve_purchase_request,
    create_purchase_request,
    discrepancy_report,
    issue_purchase_order,
    record_delivery,
    record_supplier_invoice,
    submit_for_approval,
    submit_quotation,
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
def procurement_setup(db):
    school_a = School.objects.create(name="Alpha Academy", code="ALPHA")
    school_b = School.objects.create(name="Beta School", code="BETA")

    dept_a = Department.objects.create(school=school_a, name="Science")
    dept_b = Department.objects.create(school=school_b, name="Finance")

    supplier_a1 = Supplier.objects.create(school=school_a, name="ABC Supplies")
    supplier_a2 = Supplier.objects.create(school=school_a, name="XYZ Traders")

    # Roles shaped exactly like real seed_rbac.py -- approve-only for
    # Principal, create-only for Officer -- specifically to avoid the
    # "test fixture is more permissive than reality" mistake from Phase 4a.
    officer_role = make_role(
        "Officer",
        [
            "procurement.view_procurement", "procurement.create_purchase_requests",
            "procurement.manage_quotations", "procurement.issue_purchase_orders",
            "procurement.record_deliveries", "procurement.record_supplier_invoices",
        ],
    )
    principal_role = make_role("Principal", ["procurement.view_procurement", "procurement.approve_purchase_requests"])

    officer_a = User.objects.create_user(email="officer@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=officer_a, role=officer_role)

    principal_a = User.objects.create_user(email="principal@alpha.test", password="pass12345", school=school_a)
    UserRole.objects.create(user=principal_a, role=principal_role)

    officer_b = User.objects.create_user(email="officer@beta.test", password="pass12345", school=school_b)
    UserRole.objects.create(user=officer_b, role=officer_role)

    return {
        "school_a": school_a, "school_b": school_b,
        "dept_a": dept_a, "dept_b": dept_b,
        "supplier_a1": supplier_a1, "supplier_a2": supplier_a2,
        "officer_a": officer_a, "principal_a": principal_a, "officer_b": officer_b,
    }


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_approved_pr(school, department, requester, approver) -> PurchaseRequest:
    pr = create_purchase_request(
        school=school, title="Lab equipment", department=department, requested_by=requester,
        items=[{"description": "Microscopes", "quantity": 5, "unit_price": Decimal("4000.00")}],
    )
    pr = submit_for_approval(purchase_request=pr)
    return approve_purchase_request(purchase_request=pr, approver=approver)


@pytest.mark.django_db
def test_estimated_amount_computed_from_items(procurement_setup):
    d = procurement_setup
    client = auth_client(d["officer_a"])

    response = client.post(
        "/api/v1/purchase-requests/",
        {
            "title": "Lab equipment",
            "department": d["dept_a"].id,
            "items": [{"description": "Microscopes", "quantity": 5, "unit_price": "4000.00"}],
        },
        format="json",
    )

    assert response.status_code == 201
    assert Decimal(response.data["estimated_amount"]) == Decimal("20000.00")


@pytest.mark.django_db
def test_requester_cannot_approve_own_purchase_request(procurement_setup):
    d = procurement_setup
    pr = create_purchase_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], requested_by=d["officer_a"],
        items=[{"description": "Microscopes", "quantity": 1, "unit_price": Decimal("1000.00")}],
    )
    pr = submit_for_approval(purchase_request=pr)

    with pytest.raises(ProcurementWorkflowError, match="cannot approve your own"):
        approve_purchase_request(purchase_request=pr, approver=d["officer_a"])


@pytest.mark.django_db
def test_officer_without_approve_permission_gets_403_via_api(procurement_setup):
    d = procurement_setup
    client = auth_client(d["officer_a"])
    pr = create_purchase_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], requested_by=d["officer_a"],
        items=[{"description": "Microscopes", "quantity": 1, "unit_price": Decimal("1000.00")}],
    )
    pr = submit_for_approval(purchase_request=pr)

    response = client.post(f"/api/v1/purchase-requests/{pr.id}/approve/", format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_principal_approve_only_role_can_still_approve(procurement_setup):
    """Regression test (same class of bug as expenses Phase 4a): a role
    holding ONLY procurement.approve_purchase_requests, not
    create_purchase_requests, must still be able to approve via the API."""
    d = procurement_setup
    pr = create_purchase_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], requested_by=d["officer_a"],
        items=[{"description": "Microscopes", "quantity": 1, "unit_price": Decimal("1000.00")}],
    )
    pr = submit_for_approval(purchase_request=pr)
    client = auth_client(d["principal_a"])

    response = client.post(f"/api/v1/purchase-requests/{pr.id}/approve/", format="json")

    assert response.status_code == 200
    assert response.data["status"] == "approved"


@pytest.mark.django_db
def test_full_pipeline_happy_path(procurement_setup):
    d = procurement_setup
    pr = make_approved_pr(d["school_a"], d["dept_a"], d["officer_a"], d["principal_a"])

    quote1 = submit_quotation(
        school=d["school_a"], purchase_request=pr, supplier=d["supplier_a1"],
        amount=Decimal("19500.00"), notes="", submitted_by=d["officer_a"],
    )
    submit_quotation(
        school=d["school_a"], purchase_request=pr, supplier=d["supplier_a2"],
        amount=Decimal("21000.00"), notes="", submitted_by=d["officer_a"],
    )

    po = issue_purchase_order(purchase_request=pr, quotation=quote1, issued_by=d["officer_a"])
    assert po.amount == Decimal("19500.00")
    assert po.supplier_id == d["supplier_a1"].id

    pr.refresh_from_db()
    assert pr.status == "converted"

    delivery = record_delivery(purchase_order=po, is_complete=True, notes="All items received", received_by=d["officer_a"])
    po.refresh_from_db()
    assert po.status == "delivered"
    assert delivery.is_complete

    invoice = record_supplier_invoice(purchase_order=po, invoice_number="INV-001", amount=Decimal("19500.00"), recorded_by=d["officer_a"])
    report = discrepancy_report(purchase_order=po)
    assert report["flags"] == []  # amounts match exactly, no discrepancy


@pytest.mark.django_db
def test_discrepancy_flagged_when_invoice_differs_from_po(procurement_setup):
    d = procurement_setup
    pr = make_approved_pr(d["school_a"], d["dept_a"], d["officer_a"], d["principal_a"])
    quote = submit_quotation(
        school=d["school_a"], purchase_request=pr, supplier=d["supplier_a1"],
        amount=Decimal("10000.00"), notes="", submitted_by=d["officer_a"],
    )
    po = issue_purchase_order(purchase_request=pr, quotation=quote, issued_by=d["officer_a"])
    record_delivery(purchase_order=po, is_complete=True, notes="", received_by=d["officer_a"])

    # Invoice comes in 20% higher than the PO amount -- above the 5% threshold.
    record_supplier_invoice(purchase_order=po, invoice_number="INV-002", amount=Decimal("12000.00"), recorded_by=d["officer_a"])

    report = discrepancy_report(purchase_order=po)

    assert len(report["flags"]) == 1
    assert "differs from PO amount" in report["flags"][0]


@pytest.mark.django_db
def test_cannot_issue_po_before_pr_is_approved(procurement_setup):
    d = procurement_setup
    pr = create_purchase_request(
        school=d["school_a"], title="Lab equipment", department=d["dept_a"], requested_by=d["officer_a"],
        items=[{"description": "Microscopes", "quantity": 1, "unit_price": Decimal("1000.00")}],
    )
    # Still in draft -- never submitted or approved.
    with pytest.raises(ProcurementWorkflowError):
        submit_quotation(
            school=d["school_a"], purchase_request=pr, supplier=d["supplier_a1"],
            amount=Decimal("1000.00"), notes="", submitted_by=d["officer_a"],
        )


@pytest.mark.django_db
def test_cannot_issue_two_purchase_orders_for_same_request(procurement_setup):
    d = procurement_setup
    pr = make_approved_pr(d["school_a"], d["dept_a"], d["officer_a"], d["principal_a"])
    quote = submit_quotation(
        school=d["school_a"], purchase_request=pr, supplier=d["supplier_a1"],
        amount=Decimal("1000.00"), notes="", submitted_by=d["officer_a"],
    )
    issue_purchase_order(purchase_request=pr, quotation=quote, issued_by=d["officer_a"])

    with pytest.raises(ProcurementWorkflowError, match="converted"):
        issue_purchase_order(purchase_request=pr, quotation=quote, issued_by=d["officer_a"])


@pytest.mark.django_db
def test_user_cannot_approve_another_schools_purchase_request(procurement_setup):
    d = procurement_setup
    pr_b = create_purchase_request(
        school=d["school_b"], title="Lab equipment", department=d["dept_b"], requested_by=d["officer_b"],
        items=[{"description": "Microscopes", "quantity": 1, "unit_price": Decimal("1000.00")}],
    )
    pr_b = submit_for_approval(purchase_request=pr_b)

    client = auth_client(d["principal_a"])
    response = client.post(f"/api/v1/purchase-requests/{pr_b.id}/approve/", format="json")

    assert response.status_code == 404


@pytest.mark.django_db
def test_cannot_use_another_schools_supplier_in_quotation(procurement_setup):
    d = procurement_setup
    pr = make_approved_pr(d["school_a"], d["dept_a"], d["officer_a"], d["principal_a"])
    supplier_b = Supplier.objects.create(school=d["school_b"], name="Cross Tenant Supplier")

    client = auth_client(d["officer_a"])
    response = client.post(
        "/api/v1/quotations/",
        {"purchase_request": pr.id, "supplier": supplier_b.id, "amount": "5000.00"},
        format="json",
    )

    # supplier_b is invisible in officer_a's tenant-scoped queryset.
    assert response.status_code == 404
