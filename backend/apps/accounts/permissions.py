"""
accounts/permissions.py

DRF permission class views declare via `required_permission_codename`, e.g.:

    class ExpenseViewSet(...):
        required_permission_codename = "expenses.approve"

This checks the Role/Permission DATA, not a hardcoded role name -- so
granting/revoking access is a database change, not a code change.
Self-approval blocking (a user can't approve their own request) is a
SEPARATE check that belongs in the relevant service function, not here --
this class only answers "does this user's role allow this action at all."
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class HasRolePermission(BasePermission):
    """
    Views declare `required_permission_codename` for write actions and,
    optionally, a separate `required_permission_codename_read` for GET/HEAD/
    OPTIONS (e.g. everyone with schools.view_departments can list them, but
    only schools.manage_departments can create/edit). If no read-specific
    codename is set, the write codename covers both -- safer default than
    silently allowing all authenticated reads.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            codename = getattr(view, "required_permission_codename_read", None) or getattr(
                view, "required_permission_codename", None
            )
        else:
            codename = getattr(view, "required_permission_codename", None)

        if codename is None:
            # View didn't declare a required permission -- fail closed
            # rather than silently allowing everything through.
            return False
        return bool(request.user and request.user.is_authenticated and request.user.has_perm_code(codename))
