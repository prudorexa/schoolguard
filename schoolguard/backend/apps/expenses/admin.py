from django.contrib import admin

from .models import Expense, ExpenseItem

admin.site.register(Expense)
admin.site.register(ExpenseItem)
