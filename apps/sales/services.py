from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Sale, SaleItem
from apps.debts.models import Debt


class SaleService:

    @staticmethod
    @transaction.atomic
    def create_sale(store, items, payment_type, customer=None):
        # 1. Ombor tekshiruvi
        for item in items:
            variant = item['variant']
            if variant.quantity < item['quantity']:
                raise ValidationError(
                    f"'{variant}' uchun yetarli mahsulot yo'q. "
                    f"Omborda: {variant.quantity}, "
                    f"so'ralgan: {item['quantity']}"
                )

        # 2. Umumiy summa
        total = sum(
            item['variant'].price * item['quantity']
            for item in items
        )

        # 3. Sotuv yaratish
        sale = Sale.objects.create(
            store=store,
            customer=customer,
            total=total,
            payment_type=payment_type,
        )

        # 4. Har bir mahsulot yoziladi + ombor kamayadi
        for item in items:
            variant = item['variant']
            SaleItem.objects.create(
                sale=sale,
                variant=variant,
                quantity=item['quantity'],
                price=variant.price,
            )
            variant.quantity -= item['quantity']
            variant.save(update_fields=['quantity', 'updated_at'])

        # 5. Qarzga sotilsa — Debt avtomatik yaratiladi
        if payment_type == Sale.PaymentType.DEBT:
            if not customer:
                raise ValidationError(
                    "Qarzga sotishda mijoz ko'rsatilishi kerak."
                )
            Debt.objects.create(
                customer=customer,
                store=store,
                amount=total,
            )

        return sale