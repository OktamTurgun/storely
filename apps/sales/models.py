from django.db import models
from core.models import BaseModel


class Sale(BaseModel):
    class PaymentType(models.TextChoices):
        CASH = 'cash', 'Naqd'
        DEBT = 'debt', 'Qarzga'
        CARD = 'card', 'Karta'

    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='sales'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='sales'
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        default=PaymentType.CASH
    )
    sold_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} — {self.total} so'm"


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name='items'
    )
    variant = models.ForeignKey(
        'inventory.ProductVariant',
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.variant} x {self.quantity}"

    def get_subtotal(self):
        return self.quantity * self.price
