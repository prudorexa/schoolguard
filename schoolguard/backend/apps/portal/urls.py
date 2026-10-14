from django.urls import path

from .views import ChildDetailView, ChildInvoicesView, ChildPaymentsView, MyChildrenView, ReceiptPDFView

urlpatterns = [
    path("portal/children/", MyChildrenView.as_view(), name="portal-children"),
    path("portal/children/<int:student_id>/", ChildDetailView.as_view(), name="portal-child-detail"),
    path("portal/children/<int:student_id>/invoices/", ChildInvoicesView.as_view(), name="portal-child-invoices"),
    path("portal/children/<int:student_id>/payments/", ChildPaymentsView.as_view(), name="portal-child-payments"),
    path("portal/receipts/<int:receipt_id>/pdf/", ReceiptPDFView.as_view(), name="portal-receipt-pdf"),
]
