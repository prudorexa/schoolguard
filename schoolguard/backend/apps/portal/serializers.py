from rest_framework import serializers

from fees.models import Invoice, InvoiceItem, Payment
from students.models import Student


class ChildSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True, default=None)
    total_billed = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "first_name", "last_name", "full_name",
            "school_class_name", "status", "total_billed", "total_paid", "balance",
        ]


class ChildInvoiceItemSerializer(serializers.ModelSerializer):
    fee_category_name = serializers.CharField(source="fee_category.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "fee_category_name", "description", "amount"]


class ChildInvoiceSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source="term.name", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items = ChildInvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "term_name", "total_amount", "amount_paid", "balance", "status", "items", "created_at"]


class ChildPaymentSerializer(serializers.ModelSerializer):
    invoice_term = serializers.CharField(source="invoice.term.name", read_only=True)
    receipt_number = serializers.CharField(source="receipt.receipt_number", read_only=True, default=None)
    receipt_id = serializers.IntegerField(source="receipt.id", read_only=True, default=None)

    class Meta:
        model = Payment
        fields = ["id", "invoice", "invoice_term", "amount", "method", "reference_number", "receipt_number", "receipt_id", "paid_at"]
