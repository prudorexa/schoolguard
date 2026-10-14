"""
parent_portal/permissions.py

Deliberately NOT built on HasRolePermission/TenantScopedViewSetMixin --
those answer "can this role see data across the whole school," which is
exactly wrong for a parent. A parent's access is scoped to specific
students via StudentParent links, not to the school as a whole, so this
app checks that relationship directly in every view instead of a
permission codename.
"""

from rest_framework.permissions import BasePermission


class IsParentUser(BasePermission):
    message = "This account is not linked to a parent profile."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "parent_profile")
            and request.user.parent_profile is not None
        )
