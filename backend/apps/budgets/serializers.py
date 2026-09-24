from decimal import Decimal

from rest_framework import serializers

from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    term_name = serializers.CharField(source="term.name", read_only=True)

    class Meta:
        model = Budget
        fields = ["id", "term", "term_name", "department", "department_name", "allocated_amount", "warning_threshold_pct", "created_at"]
        read_only_fields = ["id", "created_at"]


class BudgetStatusSerializer(serializers.Serializer):
    budget_id = serializers.IntegerField()
    department = serializers.CharField()
    term = serializers.CharField()
    allocated_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    utilization_pct = serializers.DecimalField(max_digits=6, decimal_places=2)
    is_over_budget = serializers.BooleanField()
    is_near_threshold = serializers.BooleanField()
