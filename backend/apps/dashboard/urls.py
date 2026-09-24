from django.urls import path

from .views import FinancialAlertsView, FinancialSummaryView

urlpatterns = [
    path("dashboard/summary/", FinancialSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/alerts/", FinancialAlertsView.as_view(), name="dashboard-alerts"),
]
