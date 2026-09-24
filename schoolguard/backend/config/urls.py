"""
SchoolGuard URL configuration.

/api/v1/... is where every app's router gets included as it's built
(accounts, schools, students, ...). Auth + a health check exist from day one
so the frontend and CI have something real to hit immediately.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health(request):
    return JsonResponse({"status": "ok", "service": "schoolguard-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("schools.urls")),
    path("api/v1/", include("students.urls")),
]
