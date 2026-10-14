"""
students/services.py

create_parent_login is the one piece of write logic in this app that isn't
plain CRUD: it creates a User and links it to an existing Parent record,
granting that parent portal access. Deliberately staff-initiated (gated by
students.manage_parents, same as editing a parent record) rather than
public self-registration -- matches the blueprint's onboarding model
(schools/parents are onboarded by staff, not self-serve) and avoids an
open account-creation endpoint that could be used to mint arbitrary users.
"""

from accounts.models import User

from .models import Parent


class ParentLoginError(Exception):
    pass


def create_parent_login(*, parent: Parent, email: str, password: str) -> User:
    if parent.user_id is not None:
        raise ParentLoginError("This parent already has a portal login.")
    if User.objects.filter(email=email).exists():
        raise ParentLoginError("A user with this email already exists.")

    user = User.objects.create_user(email=email, password=password, school=parent.school)
    parent.user = user
    parent.save(update_fields=["user"])
    return user
