from rest_framework import serializers

from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "tax_id", "status", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]
