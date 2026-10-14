"""
portal/permissions.py

Parent portal access is NOT the staff RBAC system (accounts.permissions.
HasRolePermission) -- a parent has no Role/Permission grants at all, and
shouldn't need any. The rule here is structurally different and much
narrower: "are you a parent, linked to a real Parent record" -- ownership
of *which* children is enforced separately, per-object, in services.py,
not by this permission class (which only answers "is this a parent
account at all").
"""

from rest_framework.permissions import BasePermission


class IsLinkedParent(BasePermission):
    message = "This account is not linked to a parent profile."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "parent_profile", None) is not None
        )
