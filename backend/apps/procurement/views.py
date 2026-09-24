"""
procurement/views.py

Same discipline as expenses/views.py, including the fix from that bug:
`get_permissions()` is overridden per-action so a role holding only
`procurement.approve_purchase_requests` (and not `create_purchase_requests`)
can still use the approve action -- the class-level permission never
implicitly gates a different action's endpoint.

Every FK a client supplies (purchase_request, supplier, quotation,
purchase_order) is resolved through a tenant-scoped queryset before use --
never trusted as "some object with this ID," always "some object with this
ID that belongs to the caller's school."
"""

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasRolePermission
from schools.mixins import TenantScopedViewSetMixin

from . import services
from .models import Delivery, PurchaseOrder, PurchaseRequest, Quotation, SupplierInvoice
from .serializers import (
    DeliveryCreateSerializer,
    DeliverySerializer,
    DiscrepancyReportSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderSerializer,
    PurchaseRequestCreateSerializer,
    PurchaseRequestRejectionSerializer,
    PurchaseRequestSerializer,
    QuotationCreateSerializer,
    QuotationSerializer,
    SupplierInvoiceCreateSerializer,
    SupplierInvoiceSerializer,
)


def _scoped(model, request):
    return model.objects.filter(school=request.user.school)


class PurchaseRequestViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = PurchaseRequestSerializer
    queryset = PurchaseRequest.objects.select_related("department", "requested_by", "approved_by").prefetch_related("items").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "procurement.create_purchase_requests"
    required_permission_codename_read = "procurement.view_procurement"

    def get_permissions(self):
        if self.action in ("submit", "approve", "reject"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        input_serializer = PurchaseRequestCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        from schools.models import Department

        department = get_object_or_404(_scoped(Department, request), id=data["department"])

        try:
            pr = services.create_purchase_request(
                school=request.user.school, title=data["title"], department=department,
                requested_by=request.user, items=data["items"],
            )
        except services.ProcurementValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(PurchaseRequestSerializer(pr).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        if not request.user.has_perm_code("procurement.create_purchase_requests"):
            raise PermissionDenied("You do not have permission to submit purchase requests.")
        pr = self.get_object()
        try:
            pr = services.submit_for_approval(purchase_request=pr)
        except services.ProcurementWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.has_perm_code("procurement.approve_purchase_requests"):
            raise PermissionDenied("You do not have permission to approve purchase requests.")
        pr = self.get_object()
        try:
            pr = services.approve_purchase_request(purchase_request=pr, approver=request.user)
        except services.ProcurementWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(PurchaseRequestSerializer(pr).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.has_perm_code("procurement.approve_purchase_requests"):
            raise PermissionDenied("You do not have permission to reject purchase requests.")
        pr = self.get_object()
        input_serializer = PurchaseRequestRejectionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            pr = services.reject_purchase_request(
                purchase_request=pr, approver=request.user, reason=input_serializer.validated_data["reason"]
            )
        except (services.ProcurementWorkflowError, services.ProcurementValidationError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(PurchaseRequestSerializer(pr).data)


class QuotationViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = QuotationSerializer
    queryset = Quotation.objects.select_related("supplier", "purchase_request", "submitted_by").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "procurement.manage_quotations"
    required_permission_codename_read = "procurement.view_procurement"

    def create(self, request, *args, **kwargs):
        input_serializer = QuotationCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        from suppliers.models import Supplier

        pr = get_object_or_404(_scoped(PurchaseRequest, request), id=data["purchase_request"])
        supplier = get_object_or_404(_scoped(Supplier, request), id=data["supplier"])

        try:
            quotation = services.submit_quotation(
                school=request.user.school, purchase_request=pr, supplier=supplier,
                amount=data["amount"], notes=data.get("notes", ""), submitted_by=request.user,
            )
        except services.ProcurementWorkflowError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(QuotationSerializer(quotation).data, status=status.HTTP_201_CREATED)


class PurchaseOrderViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = PurchaseOrderSerializer
    queryset = PurchaseOrder.objects.select_related("purchase_request", "supplier", "issued_by", "selected_quotation").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "procurement.issue_purchase_orders"
    required_permission_codename_read = "procurement.view_procurement"

    def get_permissions(self):
        if self.action == "discrepancy":
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        input_serializer = PurchaseOrderCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        pr = get_object_or_404(_scoped(PurchaseRequest, request), id=data["purchase_request"])
        quotation = get_object_or_404(_scoped(Quotation, request), id=data["quotation"])

        try:
            po = services.issue_purchase_order(purchase_request=pr, quotation=quotation, issued_by=request.user)
        except (services.ProcurementWorkflowError, services.ProcurementValidationError) as exc:
            raise ValidationError(str(exc)) from exc

        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def discrepancy(self, request, pk=None):
        if not request.user.has_perm_code("procurement.view_procurement"):
            raise PermissionDenied("You do not have permission to view procurement records.")
        po = self.get_object()
        report = services.discrepancy_report(purchase_order=po)
        return Response(DiscrepancyReportSerializer(report).data)


class DeliveryViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = DeliverySerializer
    queryset = Delivery.objects.select_related("purchase_order", "received_by").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "procurement.record_deliveries"
    required_permission_codename_read = "procurement.view_procurement"

    def create(self, request, *args, **kwargs):
        input_serializer = DeliveryCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        po = get_object_or_404(_scoped(PurchaseOrder, request), id=data["purchase_order"])

        try:
            delivery = services.record_delivery(
                purchase_order=po, is_complete=data["is_complete"], notes=data.get("notes", ""), received_by=request.user,
            )
        except services.ProcurementWorkflowError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(DeliverySerializer(delivery).data, status=status.HTTP_201_CREATED)


class SupplierInvoiceViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = SupplierInvoiceSerializer
    queryset = SupplierInvoice.objects.select_related("purchase_order", "recorded_by").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "procurement.record_supplier_invoices"
    required_permission_codename_read = "procurement.view_procurement"

    def create(self, request, *args, **kwargs):
        input_serializer = SupplierInvoiceCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        po = get_object_or_404(_scoped(PurchaseOrder, request), id=data["purchase_order"])

        try:
            invoice = services.record_supplier_invoice(
                purchase_order=po, invoice_number=data.get("invoice_number", ""),
                amount=data["amount"], recorded_by=request.user,
            )
        except services.ProcurementWorkflowError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(SupplierInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
