from django.core.exceptions import ValidationError
from .models import Debt


class DebtService:

    @staticmethod
    def pay_debt(debt, amount):
        if amount <= 0:
            raise ValidationError("To'lov musbat bo'lishi kerak.")
        if amount > debt.remaining:
            raise ValidationError(
                f"To'lov summasi qoldiq qarzdan "
                f"({debt.remaining}) ko'p."
            )
        debt.pay(amount)
        return debt

    @staticmethod
    def get_store_debts(store, closed=False):
        return Debt.objects.filter(
            store=store,
            is_closed=closed,
            is_deleted=False,
        ).select_related('customer').order_by('-created_at')