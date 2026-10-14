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

`perform_create` also catches IntegrityError from DB-level uniqueness
constraints (Meta.constraints = [UniqueConstraint(...)]) and converts it to
a clean 400 ValidationError. This matters because DRF's ModelSerializer
only auto-generates client-facing uniqueness validation for the older
Meta.unique_together style, NOT for Meta.constraints -- a gap discovered
live while building the Suppliers frontend, where a duplicate supplier
name produced a raw 500 Internal Server Error (a full Django debug
traceback) instead of the clean 400 every other duplicate-check in this
project returns. This is the single place every "ordinary CRUD" viewset
(Department, Class, AcademicYear, Term, FeeCategory, Supplier, ...) calls
through, so fixing it here fixes all of them at once, rather than adding a
one-off validate_name() to each serializer individually.
"""

from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError


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
        try:
            with transaction.atomic():
                serializer.save(school=user.school)
        except IntegrityError:
            raise ValidationError(
                "A record with these details already exists for your school."
            ) from None
