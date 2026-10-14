from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from . import services
from .models import Budget
from .serializers import BudgetSerializer, BudgetStatusSerializer


class BudgetViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = BudgetSerializer
    queryset = Budget.objects.select_related("department", "term").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "budgets.manage_budgets"
    required_permission_codename_read = "budgets.view_budgets"

    def get_permissions(self):
        if self.action == "status":
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        if not request.user.has_perm_code("budgets.view_budgets"):
            raise PermissionDenied("You do not have permission to view budgets.")
        budget = self.get_object()
        report = services.budget_status(budget=budget)
        return Response(BudgetStatusSerializer(report).data)
