from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from . import services
from .models import Parent, Student, StudentParent
from .serializers import CreateParentLoginSerializer, ParentSerializer, StudentParentSerializer, StudentSerializer


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

    @action(detail=True, methods=["post"], url_path="create-login")
    def create_login(self, request, pk=None):
        # Gated by the same class-level permission_classes as every other
        # write on this viewset (students.manage_parents) -- creating a
        # portal login is exactly as sensitive as editing a parent record,
        # so it doesn't need its own separate permission tier.
        parent = self.get_object()
        input_serializer = CreateParentLoginSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            services.create_parent_login(
                parent=parent,
                email=input_serializer.validated_data["email"],
                password=input_serializer.validated_data["password"],
            )
        except services.ParentLoginError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(ParentSerializer(parent).data, status=201)


class StudentParentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = StudentParentSerializer
    queryset = StudentParent.objects.select_related("student", "parent").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "students.manage_students"
    required_permission_codename_read = "students.view_students"
