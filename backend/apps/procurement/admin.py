from django.contrib import admin

from .models import Delivery, PurchaseOrder, PurchaseRequest, PurchaseRequestItem, Quotation, SupplierInvoice

admin.site.register(PurchaseRequest)
admin.site.register(PurchaseRequestItem)
admin.site.register(Quotation)
admin.site.register(PurchaseOrder)
admin.site.register(Delivery)
admin.site.register(SupplierInvoice)
