from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "suppliers.manage_suppliers"
    required_permission_codename_read = "suppliers.view_suppliers"
