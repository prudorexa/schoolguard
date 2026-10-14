"""
portal/views.py

Every view here calls services.get_child_or_404 (or the receipt
equivalent) before returning anything -- ownership is re-checked on every
single request, not cached or assumed from a prior call. A parent who
guesses another family's student_id in the URL gets a 404, the same
"structurally invisible" pattern used for cross-school isolation
everywhere else in this project, just scoped one level narrower.
"""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .permissions import IsLinkedParent
from .serializers import ChildInvoiceSerializer, ChildPaymentSerializer, ChildSummarySerializer


class MyChildrenView(APIView):
    permission_classes = [IsAuthenticated, IsLinkedParent]

    def get(self, request):
        children = services.get_children(request.user)
        data = []
        for child in children:
            summary = services.child_fee_summary(child)
            serialized = ChildSummarySerializer(child).data
            serialized.update(
                {k: str(v) for k, v in summary.items()}
            )
            data.append(serialized)
        return Response(data)


class ChildDetailView(APIView):
    permission_classes = [IsAuthenticated, IsLinkedParent]

    def get(self, request, student_id):
        child = services.get_child_or_404(user=request.user, student_id=student_id)
        summary = services.child_fee_summary(child)
        data = ChildSummarySerializer(child).data
        data.update({k: str(v) for k, v in summary.items()})
        return Response(data)


class ChildInvoicesView(APIView):
    permission_classes = [IsAuthenticated, IsLinkedParent]

    def get(self, request, student_id):
        child = services.get_child_or_404(user=request.user, student_id=student_id)
        invoices = services.get_child_invoices(child)
        return Response(ChildInvoiceSerializer(invoices, many=True).data)


class ChildPaymentsView(APIView):
    permission_classes = [IsAuthenticated, IsLinkedParent]

    def get(self, request, student_id):
        child = services.get_child_or_404(user=request.user, student_id=student_id)
        payments = services.get_child_payment_history(child)
        return Response(ChildPaymentSerializer(payments, many=True).data)


class ReceiptPDFView(APIView):
    permission_classes = [IsAuthenticated, IsLinkedParent]

    def get(self, request, receipt_id):
        receipt = services.get_receipt_for_parent_or_404(user=request.user, receipt_id=receipt_id)
        pdf_bytes = services.generate_receipt_pdf(receipt)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{receipt.receipt_number}.pdf"'
        return response
