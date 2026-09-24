"""
dashboard/views.py

Plain APIViews, not a ModelViewSet -- there's no model here, just two
read-only computed endpoints. Both are gated by dashboard.view_dashboard;
neither accepts any input beyond auth, since everything is scoped to the
caller's own school (no query params that could leak into another
tenant's numbers).
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasRolePermission

from . import services
from .serializers import FinancialAlertSerializer, FinancialSummarySerializer


class FinancialSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename_read = "dashboard.view_dashboard"

    def get(self, request):
        summary = services.financial_summary(school=request.user.school)
        return Response(FinancialSummarySerializer(summary).data)


class FinancialAlertsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename_read = "dashboard.view_dashboard"

    def get(self, request):
        alerts = services.financial_alerts(school=request.user.school)
        return Response(FinancialAlertSerializer(alerts, many=True).data)
