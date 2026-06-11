from django.db import models
from django.contrib.auth import get_user_model
from core.models import BaseModel

User = get_user_model()


class Store(BaseModel):
    class Category(models.TextChoices):
        GROCERY    = 'grocery',    'Oziq-ovqat'
        CLOTHING   = 'clothing',   'Kiyim'
        ELECTRONIC = 'electronic', 'Elektronika'
        HOUSEHOLD  = 'household',  "Ro'zg'or buyumlari"
        PHARMACY   = 'pharmacy',   'Dorixona'
        OTHER      = 'other',      'Boshqa'

    owner    = models.ForeignKey(User, on_delete=models.PROTECT, related_name='stores')
    name     = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    phone    = models.CharField(max_length=20, blank=True)
    address  = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'is_deleted']),
        ]