from django.urls import path

from .views import ChildDetailView, MyChildrenView, ReceiptDownloadView

urlpatterns = [
    path("parent-portal/children/", MyChildrenView.as_view(), name="parent-portal-children"),
    path("parent-portal/children/<int:student_id>/", ChildDetailView.as_view(), name="parent-portal-child-detail"),
    path("parent-portal/payments/<int:payment_id>/receipt/", ReceiptDownloadView.as_view(), name="parent-portal-receipt"),
]
