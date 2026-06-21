from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'telegram_id', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Telegram', {'fields': ('telegram_id',)}),
    )
