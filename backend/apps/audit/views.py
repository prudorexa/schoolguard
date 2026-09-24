from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(TenantScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only, always -- there is no create/update/delete action on this
    viewset, matching the append-only policy in models.py. Filterable by
    entity_type/entity_id so a UI can show "history for this record"."""

    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("user").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename_read = "audit.view_audit_logs"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["entity_type", "entity_id", "action"]
