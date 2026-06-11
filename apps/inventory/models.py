from django.db import models
from core.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Product(BaseModel):
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='products'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='variants_group'
    )
    name = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['store', 'is_deleted']),
            models.Index(fields=['category']),
        ]


class ProductVariant(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='variants'
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    min_threshold = models.PositiveIntegerField(default=5)
    image = models.ImageField(
        upload_to='variants/%Y/%m/',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_threshold
