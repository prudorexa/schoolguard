from decimal import Decimal

from rest_framework import serializers

from fees.models import Invoice, InvoiceItem, Payment
from students.models import Student


class ChildSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True, default=None)
    outstanding_balance = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "admission_number", "full_name", "school_class_name", "status", "outstanding_balance"]

    def get_outstanding_balance(self, obj: Student) -> str:
        total = sum((inv.balance for inv in obj.invoices.exclude(status="cancelled")), Decimal("0.00"))
        return str(total)


class ChildInvoiceItemSerializer(serializers.ModelSerializer):
    fee_category_name = serializers.CharField(source="fee_category.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "fee_category_name", "description", "amount"]


class ChildInvoiceSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source="term.name", read_only=True)
    items = ChildInvoiceItemSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "term_name", "total_amount", "amount_paid", "balance", "status", "items", "created_at"]


class ChildPaymentSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source="invoice.id", read_only=True)
    receipt_number = serializers.CharField(source="receipt.receipt_number", read_only=True, default=None)

    class Meta:
        model = Payment
        fields = ["id", "invoice_id", "amount", "method", "reference_number", "status", "receipt_number", "paid_at"]


class ChildDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    school_class_name = serializers.CharField(source="school_class.name", read_only=True, default=None)
    invoices = ChildInvoiceSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "admission_number", "first_name", "last_name", "full_name",
            "school_class_name", "status", "date_of_birth", "invoices", "payments",
        ]

    def get_payments(self, obj: Student):
        payments = Payment.objects.filter(invoice__student=obj).select_related("invoice", "receipt").order_by("-paid_at")
        return ChildPaymentSerializer(payments, many=True).data
