from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'phone', 'total_debt']
    search_fields = ['name', 'phone']
    list_filter = ['store']
