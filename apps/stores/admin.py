from django.contrib import admin
from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'owner', 'phone', 'created_at']
    list_filter = ['category']
    search_fields = ['name', 'phone']
