from django.db import models
from django.core.exceptions import ValidationError
from .models import Product, ProductVariant


class ProductService:

    @staticmethod
    def create_product(store, name, category, image=None, parent=None):
        return Product.objects.create(
            store=store,
            name=name,
            category=category,
            image=image,
            parent=parent,
        )

    @staticmethod
    def create_variant(product, name, price, quantity, min_threshold=5, image=None):
        if price <= 0:
            raise ValidationError("Narx musbat bo'lishi kerak.")
        if quantity < 0:
            raise ValidationError("Miqdor manfiy bo'lmaydi.")
        return ProductVariant.objects.create(
            product=product,
            name=name,
            price=price,
            quantity=quantity,
            min_threshold=min_threshold,
            image=image,
        )

    @staticmethod
    def restock(variant, quantity):
        if quantity <= 0:
            raise ValidationError("Kirim miqdori musbat bo'lishi kerak.")
        variant.quantity += quantity
        variant.save(update_fields=['quantity', 'updated_at'])
        return variant

    @staticmethod
    def get_low_stock(store):
        return ProductVariant.objects.filter(
            product__store=store,
            product__is_deleted=False,
            is_deleted=False,
            quantity__lte=models.F('min_threshold'),
        ).select_related('product')