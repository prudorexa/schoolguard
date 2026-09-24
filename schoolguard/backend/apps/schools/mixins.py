"""
schools/mixins.py

`TenantScopedViewSetMixin` is what every future app's viewsets
(fees, expenses, procurement, ...) inherit alongside DRF's ModelViewSet.
It's the enforcement point referenced in the blueprint's multi-tenant
architecture section: filtering happens here, automatically, so a view
can't "forget" to scope its queryset.

Super Admins (school is None) can see across all schools -- deliberately,
since platform support/onboarding needs that -- but every such cross-tenant
read should itself be audit-logged once the audit app exists (Phase 5).
"""

from rest_framework.exceptions import PermissionDenied


class TenantScopedViewSetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_super_admin:
            return qs

        if user.school_id is None:
            # Authenticated, but not attached to any school and not a
            # super admin -- shouldn't happen in practice, but fail closed.
            return qs.none()

        return qs.filter(school_id=user.school_id)

    def perform_create(self, serializer):
        user = self.request.user
        if user.school_id is None and not user.is_super_admin:
            raise PermissionDenied("User is not attached to a school.")
        serializer.save(school=user.school)
