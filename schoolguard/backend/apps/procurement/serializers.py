from decimal import Decimal

from rest_framework import serializers

from .models import Delivery, PurchaseOrder, PurchaseRequest, PurchaseRequestItem, Quotation, SupplierInvoice


class PurchaseRequestItemSerializer(serializers.ModelSerializer):
    estimated_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseRequestItem
        fields = ["id", "description", "quantity", "estimated_unit_price", "estimated_total"]
        read_only_fields = ["id"]


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = PurchaseRequestItemSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    requested_by_email = serializers.CharField(source="requested_by.email", read_only=True)
    approved_by_email = serializers.CharField(source="approved_by.email", read_only=True, default=None)
    has_purchase_order = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = [
            "id", "title", "department", "department_name", "estimated_amount", "status",
            "items", "requested_by", "requested_by_email", "approved_by", "approved_by_email",
            "approved_at", "rejection_reason", "has_purchase_order", "created_at",
        ]
        read_only_fields = fields

    def get_has_purchase_order(self, obj: PurchaseRequest) -> bool:
        return hasattr(obj, "purchase_order")


class PurchaseRequestItemInputSerializer(serializers.Serializer):
    description = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class PurchaseRequestCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    department = serializers.IntegerField()
    items = PurchaseRequestItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value


class PurchaseRequestRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)


class QuotationSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    submitted_by_email = serializers.CharField(source="submitted_by.email", read_only=True)

    class Meta:
        model = Quotation
        fields = ["id", "purchase_request", "supplier", "supplier_name", "amount", "notes", "submitted_by_email", "created_at"]
        read_only_fields = ["id", "submitted_by_email", "created_at"]


class QuotationCreateSerializer(serializers.Serializer):
    purchase_request = serializers.IntegerField()
    supplier = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    purchase_request_title = serializers.CharField(source="purchase_request.title", read_only=True)
    issued_by_email = serializers.CharField(source="issued_by.email", read_only=True)
    has_delivery = serializers.SerializerMethodField()
    has_invoice = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "purchase_request", "purchase_request_title", "selected_quotation", "supplier", "supplier_name",
            "amount", "status", "issued_by_email", "issued_at", "has_delivery", "has_invoice",
        ]
        read_only_fields = fields

    def get_has_delivery(self, obj: PurchaseOrder) -> bool:
        return hasattr(obj, "delivery")

    def get_has_invoice(self, obj: PurchaseOrder) -> bool:
        return hasattr(obj, "supplier_invoice")


class PurchaseOrderCreateSerializer(serializers.Serializer):
    purchase_request = serializers.IntegerField()
    quotation = serializers.IntegerField()


class DeliverySerializer(serializers.ModelSerializer):
    received_by_email = serializers.CharField(source="received_by.email", read_only=True)

    class Meta:
        model = Delivery
        fields = ["id", "purchase_order", "is_complete", "notes", "received_by_email", "delivered_at"]
        read_only_fields = fields


class DeliveryCreateSerializer(serializers.Serializer):
    purchase_order = serializers.IntegerField()
    is_complete = serializers.BooleanField(default=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class SupplierInvoiceSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.CharField(source="recorded_by.email", read_only=True)

    class Meta:
        model = SupplierInvoice
        fields = ["id", "purchase_order", "invoice_number", "amount", "recorded_by_email", "received_at"]
        read_only_fields = fields


class SupplierInvoiceCreateSerializer(serializers.Serializer):
    purchase_order = serializers.IntegerField()
    invoice_number = serializers.CharField(required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class DiscrepancyReportSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    po_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    invoiced_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    delivered = serializers.BooleanField()
    flags = serializers.ListField(child=serializers.CharField())
