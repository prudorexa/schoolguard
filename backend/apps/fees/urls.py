from rest_framework.routers import DefaultRouter

from .views import FeeCategoryViewSet, FeeStructureViewSet, InvoiceViewSet, PaymentViewSet, ReceiptViewSet

router = DefaultRouter()
router.register("fee-categories", FeeCategoryViewSet, basename="fee-category")
router.register("fee-structures", FeeStructureViewSet, basename="fee-structure")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")
router.register("receipts", ReceiptViewSet, basename="receipt")

urlpatterns = router.urls
