from django.contrib import admin
from .models import Debt


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['customer', 'store', 'amount', 'paid', 'remaining', 'is_closed', 'created_at']
    list_filter = ['is_closed', 'store']
    search_fields = ['customer__name']
    readonly_fields = ['remaining']
