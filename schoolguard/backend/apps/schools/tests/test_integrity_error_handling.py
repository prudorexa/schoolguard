"""
Regression test for a real bug found live while building the Suppliers
frontend: models using Meta.constraints = [UniqueConstraint(...)] (as
opposed to the older Meta.unique_together) don't get automatic DRF
uniqueness validation, so a duplicate would previously 500 with a raw
Django debug traceback instead of a clean 400. Fixed centrally in
TenantScopedViewSetMixin.perform_create -- tested here against Department,
which is representative of every "ordinary CRUD" viewset sharing that
mixin (Class, AcademicYear, Term, FeeCategory, Supplier, ...).
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from schools.models import Department, School


@pytest.mark.django_db
def test_duplicate_department_name_returns_clean_400_not_500():
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    Department.objects.create(school=school, name="Science")

    role = Role.objects.create(name="Admin")
    for codename in ["schools.view_departments", "schools.manage_departments"]:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    user = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=user, role=role)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/departments/", {"name": "Science"})

    assert response.status_code == 400
    assert Department.objects.filter(school=school, name="Science").count() == 1


@pytest.mark.django_db
def test_creating_department_still_works_normally_after_the_fix():
    """The fix wraps perform_create in an inner atomic block -- confirms
    that doesn't break the ordinary, non-duplicate case."""
    school = School.objects.create(name="Alpha Academy", code="ALPHA")
    role = Role.objects.create(name="Admin")
    for codename in ["schools.view_departments", "schools.manage_departments"]:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    user = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school)
    UserRole.objects.create(user=user, role=role)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/v1/departments/", {"name": "Mathematics"})

    assert response.status_code == 201
    assert Department.objects.filter(school=school, name="Mathematics").exists()
