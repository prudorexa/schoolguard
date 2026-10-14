from rest_framework import serializers

from .models import Parent, Student, StudentParent


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "first_name", "last_name", "full_name",
            "date_of_birth", "school_class", "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_admission_number(self, value: str) -> str:
        # Extra guard beyond the DB constraint so the client gets a clean
        # 400 with a clear message instead of a raw IntegrityError.
        school = self.context["request"].user.school
        qs = Student.objects.filter(school=school, admission_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A student with this admission number already exists.")
        return value


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Parent
        fields = ["id", "first_name", "last_name", "full_name", "phone", "email", "created_at"]
        read_only_fields = ["id", "created_at"]


class StudentParentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    parent_name = serializers.CharField(source="parent.full_name", read_only=True)

    class Meta:
        model = StudentParent
        fields = ["id", "student", "student_name", "parent", "parent_name", "relationship", "is_primary_contact"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # Cross-tenant guard: the student and parent chosen must belong to
        # the caller's own school (queryset filtering on the FK fields
        # doesn't happen automatically for related-object choices, so this
        # is checked explicitly rather than assumed).
        request = self.context["request"]
        student = attrs.get("student") or getattr(self.instance, "student", None)
        parent = attrs.get("parent") or getattr(self.instance, "parent", None)
        if student and student.school_id != request.user.school_id:
            raise serializers.ValidationError("Student does not belong to your school.")
        if parent and parent.school_id != request.user.school_id:
            raise serializers.ValidationError("Parent does not belong to your school.")
        return attrs


class CreateParentLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
