from rest_framework.routers import DefaultRouter

from .views import DeliveryViewSet, PurchaseOrderViewSet, PurchaseRequestViewSet, QuotationViewSet, SupplierInvoiceViewSet

router = DefaultRouter()
router.register("purchase-requests", PurchaseRequestViewSet, basename="purchase-request")
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("deliveries", DeliveryViewSet, basename="delivery")
router.register("supplier-invoices", SupplierInvoiceViewSet, basename="supplier-invoice")

urlpatterns = router.urls
