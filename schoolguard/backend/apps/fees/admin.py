from django.contrib import admin

from .models import FeeCategory, FeeStructure, Invoice, InvoiceItem, Payment, Receipt

admin.site.register(FeeCategory)
admin.site.register(FeeStructure)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
admin.site.register(Receipt)
