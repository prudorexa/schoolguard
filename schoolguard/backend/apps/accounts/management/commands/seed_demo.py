"""
Creates (or repairs) a demo school and School Admin login in one command.

Idempotent: safe to run repeatedly. If the admin user already exists, its
password is RESET to the one given -- which is exactly what you want when
"the admin login stopped working" (e.g. after cloning the repo somewhere
new, where the gitignored db.sqlite3 didn't come along).

Usage:
    python manage.py migrate
    python manage.py seed_demo
    python manage.py seed_demo --email me@school.test --password 'S0me-long-pass'

Local/demo use only: don't run this with a guessable password against a
real deployment.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User, UserRole
from schools.models import School


class Command(BaseCommand):
    help = "Seed RBAC + a demo school + a School Admin login (idempotent; resets the password)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@school.test")
        parser.add_argument("--password", default="demo12345")

    @transaction.atomic
    def handle(self, *args, **options):
        email, password = options["email"], options["password"]

        call_command("seed_rbac", verbosity=0)

        school, _ = School.objects.get_or_create(code="DEMO", defaults={"name": "Demo School"})
        role = Role.objects.get(name="School Admin", school=None)

        user, created = User.objects.get_or_create(email=email, defaults={"school": school})
        user.school = school
        user.is_active = True
        user.set_password(password)
        user.save()
        UserRole.objects.get_or_create(user=user, role=role)

        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Reset password for'} School Admin: {email}"
        ))
