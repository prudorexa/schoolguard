"""
Seeds the platform-default roles and permissions so local dev / a fresh
school onboarding doesn't start from an empty RBAC table. Idempotent --
safe to re-run.

Usage: python manage.py seed_rbac
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role, RolePermission

PLATFORM_ROLES = [
    "Super Admin",
    "School Admin",
    "Principal",
    "Accountant",
    "Procurement Officer",
    "Department Head",
    "Teacher",
    "Auditor",
    "Parent",
]

# Grows as each module ships (Phase 3 adds fees.*, Phase 4 adds expenses.*,
# etc). Kept here rather than a migration so it's easy to extend without a
# new migration every time a permission is added.
PERMISSIONS = [
    ("schools.view_departments", "View departments"),
    ("schools.manage_departments", "Create/edit/delete departments"),
    ("schools.view_academic_years", "View academic years and terms"),
    ("schools.manage_academic_years", "Create/edit/delete academic years and terms"),
    ("schools.view_classes", "View classes"),
    ("schools.manage_classes", "Create/edit/delete classes"),
    ("students.view_students", "View students"),
    ("students.manage_students", "Create/edit/delete students"),
    ("students.view_parents", "View parents"),
    ("students.manage_parents", "Create/edit/delete parents"),
]

# role_name -> list of permission codenames. Principal and Auditor get
# read access to everything by convention; write access is granted
# module-by-module as each is built.
ROLE_PERMISSIONS = {
    "School Admin": [
        "schools.view_departments", "schools.manage_departments",
        "schools.view_academic_years", "schools.manage_academic_years",
        "schools.view_classes", "schools.manage_classes",
        "students.view_students", "students.manage_students",
        "students.view_parents", "students.manage_parents",
    ],
    "Principal": [
        "schools.view_departments", "schools.view_academic_years",
        "schools.view_classes", "students.view_students", "students.view_parents",
    ],
    "Teacher": ["students.view_students"],
    "Auditor": [
        "schools.view_departments", "schools.view_academic_years",
        "schools.view_classes", "students.view_students", "students.view_parents",
    ],
}


class Command(BaseCommand):
    help = "Seed platform-default roles and permissions (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        for codename, description in PERMISSIONS:
            _, created = Permission.objects.get_or_create(
                codename=codename, defaults={"description": description}
            )
            self.stdout.write(f"{'created' if created else 'exists '} permission: {codename}")

        for name in PLATFORM_ROLES:
            _, created = Role.objects.get_or_create(name=name, school=None)
            self.stdout.write(f"{'created' if created else 'exists '} role: {name}")

        for role_name, codenames in ROLE_PERMISSIONS.items():
            role = Role.objects.get(name=role_name, school=None)
            for codename in codenames:
                perm = Permission.objects.get(codename=codename)
                RolePermission.objects.get_or_create(role=role, permission=perm)

        self.stdout.write(self.style.SUCCESS("RBAC seed complete."))
