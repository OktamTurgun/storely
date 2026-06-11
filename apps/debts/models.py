from django.db import models
from core.models import BaseModel


class Debt(BaseModel):
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='debts'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_closed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer.name} — {self.remaining} so'm"

    @property
    def remaining(self):
        return self.amount - self.paid

    def pay(self, amount):
        self.paid += amount
        if self.paid >= self.amount:
            self.is_closed = True
        self.save(update_fields=['paid', 'is_closed', 'updated_at'])
