from rest_framework import serializers


class RecentTransactionSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    date = serializers.DateTimeField(allow_null=True)
    description = serializers.CharField()


class FinancialSummarySerializer(serializers.Serializer):
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_position = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_allocated = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_utilization_pct = serializers.DecimalField(max_digits=6, decimal_places=2)
    pending_expense_approvals = serializers.IntegerField()
    recent_transactions = RecentTransactionSerializer(many=True)


class FinancialAlertSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=["critical", "warning"])
    category = serializers.CharField()
    message = serializers.CharField()
