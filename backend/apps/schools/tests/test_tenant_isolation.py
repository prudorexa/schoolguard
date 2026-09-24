"""
This test is the one the blueprint calls out as mandatory before any other
app gets built on top of accounts + schools: proof that one school's data
is structurally unreachable by another school's users, through the real
API (not by poking the ORM directly, which would prove less).
"""

import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from schools.models import Department, School


@pytest.fixture
def two_schools_with_users(db):
    school_a = School.objects.create(name="Alpha Academy", code="ALPHA")
    school_b = School.objects.create(name="Beta School", code="BETA")

    view_perm = Permission.objects.create(codename="schools.view_departments")
    manage_perm = Permission.objects.create(codename="schools.manage_departments")

    role = Role.objects.create(name="Admin")
    RolePermission.objects.create(role=role, permission=view_perm)
    RolePermission.objects.create(role=role, permission=manage_perm)

    user_a = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school_a)
    user_b = User.objects.create_user(email="admin@beta.test", password="pass12345", school=school_b)
    UserRole.objects.create(user=user_a, role=role)
    UserRole.objects.create(user=user_b, role=role)

    dept_a = Department.objects.create(school=school_a, name="Science")
    dept_b = Department.objects.create(school=school_b, name="Finance")

    return {
        "school_a": school_a,
        "school_b": school_b,
        "user_a": user_a,
        "user_b": user_b,
        "dept_a": dept_a,
        "dept_b": dept_b,
    }


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_user_only_sees_own_schools_departments_in_list(two_schools_with_users):
    data = two_schools_with_users
    client = auth_client(data["user_a"])

    response = client.get("/api/v1/departments/")

    assert response.status_code == 200
    returned_ids = {row["id"] for row in response.data["results"]}
    assert data["dept_a"].id in returned_ids
    assert data["dept_b"].id not in returned_ids


@pytest.mark.django_db
def test_user_cannot_retrieve_another_schools_department_by_id(two_schools_with_users):
    data = two_schools_with_users
    client = auth_client(data["user_a"])

    response = client.get(f"/api/v1/departments/{data['dept_b'].id}/")

    # Must not be 200 -- 404 because the queryset never included it in the
    # first place, which is the point: not a 403 "found it, blocked it",
    # but structurally invisible.
    assert response.status_code == 404


@pytest.mark.django_db
def test_created_department_is_stamped_with_creators_school_not_client_input(two_schools_with_users):
    data = two_schools_with_users
    client = auth_client(data["user_a"])

    # Even if a malicious/buggy client tried to pass a school id, the
    # serializer doesn't expose `school` as writable -- perform_create
    # always uses request.user.school.
    response = client.post("/api/v1/departments/", {"name": "Sports"})

    assert response.status_code == 201
    created = Department.objects.get(id=response.data["id"])
    assert created.school_id == data["school_a"].id


@pytest.mark.django_db
def test_user_without_required_permission_is_denied(two_schools_with_users):
    data = two_schools_with_users
    unprivileged = User.objects.create_user(
        email="noperm@alpha.test", password="pass12345", school=data["school_a"]
    )
    client = auth_client(unprivileged)

    response = client.get("/api/v1/departments/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_super_admin_sees_departments_across_schools(two_schools_with_users):
    data = two_schools_with_users
    super_admin = User.objects.create_superuser(email="platform@schoolguard.test", password="pass12345")

    client = auth_client(super_admin)
    response = client.get("/api/v1/departments/")

    assert response.status_code == 200
    returned_ids = {row["id"] for row in response.data["results"]}
    assert data["dept_a"].id in returned_ids
    assert data["dept_b"].id in returned_ids
