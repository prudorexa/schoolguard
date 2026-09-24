"""
fees/serializers.py

Two serializers here are deliberately NOT plain ModelSerializers doing
serializer.save():

- InvoiceCreateSerializer only validates shape (student, term, items) --
  the actual creation goes through services.create_invoice_for_student so
  total_amount is always computed, never trusted from the client.
- PaymentCreateSerializer only validates shape -- creation goes through
  services.record_payment so the overpayment/status-recompute/receipt-
  generation logic can't be bypassed by hitting the API directly.

InvoiceSerializer / PaymentSerializer (read) expose amount_paid/balance as
computed properties, never stored client-editable fields.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import FeeCategory, FeeStructure, Invoice, InvoiceItem, Payment, Receipt


class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = ["id", "name"]
        read_only_fields = ["id"]


class FeeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = ["id", "term", "fee_category", "school_class", "amount"]
        read_only_fields = ["id"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    fee_category_name = serializers.CharField(source="fee_category.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "fee_category", "fee_category_name", "description", "amount"]
        read_only_fields = ["id"]


class InvoiceSerializer(serializers.ModelSerializer):
    """Read/list serializer -- total_amount, status, balance are all
    server-computed and read-only here; nothing about money is writable
    through this serializer."""

    items = InvoiceItemSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "student", "student_name", "term", "total_amount",
            "amount_paid", "balance", "status", "items", "created_at",
        ]
        read_only_fields = fields


class InvoiceItemInputSerializer(serializers.Serializer):
    fee_category_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class InvoiceCreateSerializer(serializers.Serializer):
    """Input-only shape for POST /invoices/ -- routed to
    services.create_invoice_for_student by the view, never to .save()."""

    student = serializers.IntegerField()
    term = serializers.IntegerField()
    items = InvoiceItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.CharField(source="recorded_by.email", read_only=True)
    receipt_number = serializers.CharField(source="receipt.receipt_number", read_only=True, default=None)

    class Meta:
        model = Payment
        fields = [
            "id", "invoice", "amount", "method", "reference_number",
            "recorded_by", "recorded_by_email", "status", "reversal_reason",
            "receipt_number", "paid_at",
        ]
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    """Input-only shape for POST /payments/ -- routed to
    services.record_payment. `recorded_by` is never accepted from the
    client -- the view sets it from request.user."""

    invoice = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=Payment.METHOD_CHOICES)
    reference_number = serializers.CharField(required=False, allow_blank=True, default="")


class PaymentReversalSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)


class ReceiptSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source="payment.invoice_id", read_only=True)
    student_name = serializers.CharField(source="payment.invoice.student.full_name", read_only=True)
    amount = serializers.DecimalField(source="payment.amount", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Receipt
        fields = ["id", "receipt_number", "payment", "invoice_id", "student_name", "amount", "created_at"]
        read_only_fields = fields
