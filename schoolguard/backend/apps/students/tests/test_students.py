import pytest
from rest_framework.test import APIClient

from accounts.models import Permission, Role, RolePermission, User, UserRole
from schools.models import School
from students.models import Parent, Student, StudentParent


@pytest.fixture
def rbac_role(db):
    perms = [
        "students.view_students", "students.manage_students",
        "students.view_parents", "students.manage_parents",
    ]
    role = Role.objects.create(name="Admin")
    for codename in perms:
        perm, _ = Permission.objects.get_or_create(codename=codename)
        RolePermission.objects.create(role=role, permission=perm)
    return role


@pytest.fixture
def two_schools_with_students(db, rbac_role):
    school_a = School.objects.create(name="Alpha Academy", code="ALPHA")
    school_b = School.objects.create(name="Beta School", code="BETA")

    user_a = User.objects.create_user(email="admin@alpha.test", password="pass12345", school=school_a)
    user_b = User.objects.create_user(email="admin@beta.test", password="pass12345", school=school_b)
    UserRole.objects.create(user=user_a, role=rbac_role)
    UserRole.objects.create(user=user_b, role=rbac_role)

    student_a = Student.objects.create(
        school=school_a, admission_number="A001", first_name="Amina", last_name="Otieno"
    )
    student_b = Student.objects.create(
        school=school_b, admission_number="A001", first_name="Brian", last_name="Kamau"
    )

    return {
        "school_a": school_a, "school_b": school_b,
        "user_a": user_a, "user_b": user_b,
        "student_a": student_a, "student_b": student_b,
    }


def auth_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_same_admission_number_allowed_across_different_schools(two_schools_with_students):
    # This is the point of scoping uniqueness to (school, admission_number)
    # rather than a bare unique=True: two unrelated schools can both have
    # a student "A001" without collision.
    data = two_schools_with_students
    assert data["student_a"].admission_number == data["student_b"].admission_number
    assert data["student_a"].school_id != data["student_b"].school_id


@pytest.mark.django_db
def test_duplicate_admission_number_within_same_school_rejected(two_schools_with_students):
    data = two_schools_with_students
    client = auth_client(data["user_a"])

    response = client.post(
        "/api/v1/students/",
        {"admission_number": "A001", "first_name": "Someone", "last_name": "Else"},
    )

    assert response.status_code == 400
    assert "admission_number" in response.data


@pytest.mark.django_db
def test_user_cannot_list_another_schools_students(two_schools_with_students):
    data = two_schools_with_students
    client = auth_client(data["user_a"])

    response = client.get("/api/v1/students/")

    returned_ids = {row["id"] for row in response.data["results"]}
    assert data["student_a"].id in returned_ids
    assert data["student_b"].id not in returned_ids


@pytest.mark.django_db
def test_cannot_link_parent_and_student_from_different_schools(two_schools_with_students):
    data = two_schools_with_students
    parent_a = Parent.objects.create(school=data["school_a"], first_name="Grace", last_name="Otieno")
    client = auth_client(data["user_a"])

    # student_b belongs to school_b; user_a (school_a) tries to link their
    # own parent to another school's student.
    response = client.post(
        "/api/v1/student-parents/",
        {"student": data["student_b"].id, "parent": parent_a.id, "relationship": "mother"},
    )

    assert response.status_code == 400
    assert not StudentParent.objects.filter(student=data["student_b"], parent=parent_a).exists()


@pytest.mark.django_db
def test_valid_student_parent_link_succeeds(two_schools_with_students):
    data = two_schools_with_students
    parent_a = Parent.objects.create(school=data["school_a"], first_name="Grace", last_name="Otieno")
    client = auth_client(data["user_a"])

    response = client.post(
        "/api/v1/student-parents/",
        {"student": data["student_a"].id, "parent": parent_a.id, "relationship": "mother", "is_primary_contact": True},
    )

    assert response.status_code == 201
    assert StudentParent.objects.filter(student=data["student_a"], parent=parent_a).exists()
