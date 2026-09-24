from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_email", "action", "entity_type", "entity_id",
            "previous_value", "new_value", "reason", "ip_address", "created_at",
        ]
        read_only_fields = fields
