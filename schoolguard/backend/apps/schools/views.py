from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasRolePermission

from .mixins import TenantScopedViewSetMixin
from .models import AcademicYear, Class, Department, Term
from .serializers import AcademicYearSerializer, ClassSerializer, DepartmentSerializer, TermSerializer


class DepartmentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """
    Tenant-scoped CRUD for departments. get_queryset()/perform_create() come
    from TenantScopedViewSetMixin -- this class only adds what's specific to
    Department: the serializer and which permission gates write access.
    """

    serializer_class = DepartmentSerializer
    queryset = Department.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "schools.manage_departments"
    required_permission_codename_read = "schools.view_departments"


class AcademicYearViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = AcademicYearSerializer
    queryset = AcademicYear.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "schools.manage_academic_years"
    required_permission_codename_read = "schools.view_academic_years"


class TermViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TermSerializer
    queryset = Term.objects.select_related("academic_year").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "schools.manage_academic_years"
    required_permission_codename_read = "schools.view_academic_years"


class ClassViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ClassSerializer
    queryset = Class.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "schools.manage_classes"
    required_permission_codename_read = "schools.view_classes"
