from rest_framework import serializers

from .models import Role, User


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    school_code = serializers.CharField(source="school.code", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "school_code", "is_super_admin", "roles"]

    def get_roles(self, obj: User) -> list[str]:
        return list(Role.objects.filter(user_roles__user=obj).values_list("name", flat=True))
