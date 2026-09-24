from decimal import Decimal

from rest_framework import serializers

from .models import Expense, ExpenseItem


class ExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseItem
        fields = ["id", "description", "amount"]
        read_only_fields = ["id"]


class ExpenseSerializer(serializers.ModelSerializer):
    """Read/list serializer. `amount` and `status` are computed/workflow-
    controlled, never writable through this serializer -- see services.py."""

    items = ExpenseItemSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    requested_by_email = serializers.CharField(source="requested_by.email", read_only=True)
    approved_by_email = serializers.CharField(source="approved_by.email", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id", "title", "department", "department_name", "term", "supplier", "supplier_name",
            "amount", "status", "items", "requested_by", "requested_by_email",
            "approved_by", "approved_by_email", "approved_at", "rejection_reason",
            "paid_at", "created_at",
        ]
        read_only_fields = fields


class ExpenseItemInputSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class ExpenseCreateSerializer(serializers.Serializer):
    """Input-only shape for POST /expenses/ -- routed to
    services.create_expense_request, never to .save()."""

    title = serializers.CharField()
    department = serializers.IntegerField()
    supplier = serializers.IntegerField(required=False, allow_null=True, default=None)
    term = serializers.IntegerField(required=False, allow_null=True, default=None)
    items = ExpenseItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value


class ExpenseRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)
