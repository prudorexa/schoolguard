from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from .models import Parent, Student, StudentParent
from .serializers import ParentSerializer, StudentParentSerializer, StudentSerializer


class StudentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.select_related("school_class").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "students.manage_students"
    required_permission_codename_read = "students.view_students"


class ParentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    queryset = Parent.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "students.manage_parents"
    required_permission_codename_read = "students.view_parents"


class StudentParentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = StudentParentSerializer
    queryset = StudentParent.objects.select_related("student", "parent").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "students.manage_students"
    required_permission_codename_read = "students.view_students"
