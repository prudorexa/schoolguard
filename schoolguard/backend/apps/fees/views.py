"""
fees/views.py

FeeCategoryViewSet / FeeStructureViewSet: ordinary tenant-scoped CRUD, same
pattern as Department/Class in the schools app.

InvoiceViewSet / PaymentViewSet: list/retrieve go through the normal
tenant-scoped queryset, but `create` is overridden to call the relevant
service function instead of `serializer.save()` -- this is what actually
makes services.py load-bearing rather than decorative. A raw POST to these
endpoints cannot skip the balance/overpayment/status-recompute logic
because there's no serializer.save() path left that would let it.
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
from .models import FeeCategory, FeeStructure, Invoice, Payment, Receipt
from .serializers import (
    FeeCategorySerializer,
    FeeStructureSerializer,
    InvoiceCreateSerializer,
    InvoiceSerializer,
    PaymentCreateSerializer,
    PaymentReversalSerializer,
    PaymentSerializer,
    ReceiptSerializer,
)


class FeeCategoryViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = FeeCategorySerializer
    queryset = FeeCategory.objects.all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "fees.manage_fee_structures"
    required_permission_codename_read = "fees.view_invoices"


class FeeStructureViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = FeeStructureSerializer
    queryset = FeeStructure.objects.select_related("term", "fee_category", "school_class").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "fees.manage_fee_structures"
    required_permission_codename_read = "fees.view_invoices"


class InvoiceViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]  # no PATCH/PUT/DELETE -- see class docstring
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("student", "term").prefetch_related("items").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "fees.manage_invoices"
    required_permission_codename_read = "fees.view_invoices"

    def create(self, request, *args, **kwargs):
        input_serializer = InvoiceCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        student = get_object_or_404(self._student_queryset(), id=data["student"])
        term = get_object_or_404(self._term_queryset(), id=data["term"])

        try:
            invoice = services.create_invoice_for_student(
                school=request.user.school,
                student=student,
                term=term,
                items=data["items"],
            )
        except services.InvoiceValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    def _student_queryset(self):
        from students.models import Student

        return Student.objects.filter(school=self.request.user.school)

    def _term_queryset(self):
        from schools.models import Term

        return Term.objects.filter(school=self.request.user.school)


class PaymentViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]  # reversal is a dedicated action, not PATCH/DELETE
    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related("invoice", "recorded_by", "receipt").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "fees.record_payments"
    required_permission_codename_read = "fees.view_invoices"

    def create(self, request, *args, **kwargs):
        input_serializer = PaymentCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        invoice = get_object_or_404(Invoice.objects.filter(school=request.user.school), id=data["invoice"])

        try:
            payment = services.record_payment(
                school=request.user.school,
                invoice=invoice,
                amount=data["amount"],
                method=data["method"],
                reference_number=data.get("reference_number", ""),
                recorded_by=request.user,
            )
        except services.PaymentValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        # Separation of duties: reversing money already recorded needs its
        # own permission, distinct from recording it -- an Accountant who
        # can record a payment shouldn't necessarily be able to un-record
        # one without someone with broader authority holding that permission.
        if not request.user.has_perm_code("fees.reverse_payments"):
            raise PermissionDenied("You do not have permission to reverse payments.")

        payment = self.get_object()
        input_serializer = PaymentReversalSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            payment = services.reverse_payment(
                payment=payment, reason=input_serializer.validated_data["reason"], actor=request.user
            )
        except services.PaymentValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(PaymentSerializer(payment).data)


class ReceiptViewSet(TenantScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Receipts are generated automatically by record_payment -- never
    created or edited directly through the API."""

    serializer_class = ReceiptSerializer
    queryset = Receipt.objects.select_related("payment", "payment__invoice", "payment__invoice__student").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename_read = "fees.view_invoices"
