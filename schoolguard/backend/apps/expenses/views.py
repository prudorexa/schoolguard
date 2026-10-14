"""
expenses/views.py

Every state-changing action is its own endpoint calling its own services.py
function -- create, submit, approve, reject, mark_paid, cancel. None of
them are a raw PATCH of `status` (http_method_names below disables
PATCH/PUT/DELETE entirely), so there's no way to skip the workflow rules
by hitting the API differently than the UI does.

Permission split (deliberate, matches the blueprint's separation-of-duties
requirement):
  expenses.create_expenses  -- create/submit/cancel your own requests
  expenses.approve_expenses -- approve/reject someone else's request
  expenses.record_expense_payment -- mark an approved expense as paid
(a School Admin/Principal typically holds all three; an Accountant might
hold create + record_payment but not approve; a Department Head might hold
only create -- see seed_rbac.py for what's actually granted to each role.)
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
from .models import Expense
from .serializers import ExpenseCreateSerializer, ExpenseRejectionSerializer, ExpenseSerializer


class ExpenseViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.select_related("department", "supplier", "requested_by", "approved_by").prefetch_related("items").all()
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission_codename = "expenses.create_expenses"
    required_permission_codename_read = "expenses.view_expenses"

    def get_permissions(self):
        # `create`/`list`/`retrieve` are gated by the class-level
        # HasRolePermission (expenses.create_expenses / view_expenses).
        # The workflow actions each enforce their OWN permission explicitly
        # in the method body (approve/reject need expenses.approve_expenses,
        # mark_paid needs expenses.record_expense_payment, submit/cancel
        # need expenses.create_expenses) -- so the class-level check is
        # deliberately bypassed here rather than incorrectly applying
        # "create_expenses" to every action, which would wrongly block a
        # Principal (who can approve but not create) from approving at all.
        if self.action in ("submit", "approve", "reject", "mark_paid", "cancel"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        input_serializer = ExpenseCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        department = get_object_or_404(self._department_queryset(), id=data["department"])
        supplier = None
        if data.get("supplier"):
            supplier = get_object_or_404(self._supplier_queryset(), id=data["supplier"])
        term = None
        if data.get("term"):
            term = get_object_or_404(self._term_queryset(), id=data["term"])

        try:
            expense = services.create_expense_request(
                school=request.user.school,
                title=data["title"],
                department=department,
                supplier=supplier,
                term=term,
                requested_by=request.user,
                items=data["items"],
            )
        except services.ExpenseValidationError as exc:
            raise ValidationError(str(exc)) from exc

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)

    def _department_queryset(self):
        from schools.models import Department

        return Department.objects.filter(school=self.request.user.school)

    def _supplier_queryset(self):
        from suppliers.models import Supplier

        return Supplier.objects.filter(school=self.request.user.school)

    def _term_queryset(self):
        from schools.models import Term

        return Term.objects.filter(school=self.request.user.school)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        if not request.user.has_perm_code("expenses.create_expenses"):
            raise PermissionDenied("You do not have permission to submit expense requests.")
        expense = self.get_object()
        try:
            expense = services.submit_for_approval(expense=expense)
        except services.ExpenseWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.has_perm_code("expenses.approve_expenses"):
            raise PermissionDenied("You do not have permission to approve expenses.")
        expense = self.get_object()
        try:
            expense = services.approve_expense(expense=expense, approver=request.user)
        except services.ExpenseWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.has_perm_code("expenses.approve_expenses"):
            raise PermissionDenied("You do not have permission to reject expenses.")
        expense = self.get_object()
        input_serializer = ExpenseRejectionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            expense = services.reject_expense(
                expense=expense, approver=request.user, reason=input_serializer.validated_data["reason"]
            )
        except (services.ExpenseWorkflowError, services.ExpenseValidationError) as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        if not request.user.has_perm_code("expenses.record_expense_payment"):
            raise PermissionDenied("You do not have permission to record expense payments.")
        expense = self.get_object()
        try:
            expense = services.mark_expense_paid(expense=expense, actor=request.user)
        except services.ExpenseWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if not request.user.has_perm_code("expenses.create_expenses"):
            raise PermissionDenied("You do not have permission to cancel expense requests.")
        expense = self.get_object()
        try:
            expense = services.cancel_expense(expense=expense, actor=request.user)
        except services.ExpenseWorkflowError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(ExpenseSerializer(expense).data)
