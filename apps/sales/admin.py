from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['variant', 'quantity', 'price']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'store', 'customer', 'total', 'payment_type', 'sold_at']
    list_filter = ['payment_type', 'store']
    readonly_fields = ['total', 'sold_at']
    inlines = [SaleItemInline]
