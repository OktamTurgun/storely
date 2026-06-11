from django.db import models
from core.models import BaseModel


class Customer(BaseModel):
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='customers'
    )
    name = models.CharField(max_length=255, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def total_debt(self):
        from apps.debts.models import Debt
        result = self.debts.filter(
            is_closed=False,
            is_deleted=False,
        ).aggregate(
            total=models.Sum('amount') - models.Sum('paid')
        )
        return result['total'] or 0

    class Meta:
        indexes = [
            models.Index(fields=['store', 'is_deleted']),
        ]
