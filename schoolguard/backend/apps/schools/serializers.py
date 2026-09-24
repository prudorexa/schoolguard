from rest_framework import serializers

from .models import AcademicYear, Class, Department, School, Term


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "code", "address", "phone", "email", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]
        # `school` deliberately NOT writable here -- it's set server-side
        # from request.user.school in TenantScopedViewSetMixin.perform_create,
        # never trusted from client input.


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "name", "start_date", "end_date", "is_current"]
        read_only_fields = ["id"]


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ["id", "academic_year", "name", "start_date", "end_date", "is_current"]
        read_only_fields = ["id"]


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]
