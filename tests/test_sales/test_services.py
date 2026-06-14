import pytest
from django.core.exceptions import ValidationError
from apps.sales.services import SaleService
from apps.sales.models import Sale
from apps.debts.models import Debt


@pytest.mark.django_db
class TestSaleService:

    def test_cash_sale_reduces_stock(self, store, variant, customer):
        original_qty = variant.quantity
        SaleService.create_sale(
            store=store,
            items=[{'variant': variant, 'quantity': 3}],
            payment_type=Sale.PaymentType.CASH,
            customer=customer,
        )
        variant.refresh_from_db()
        assert variant.quantity == original_qty - 3

    def test_sale_correct_total(self, store, variant, customer):
        sale = SaleService.create_sale(
            store=store,
            items=[{'variant': variant, 'quantity': 2}],
            payment_type=Sale.PaymentType.CASH,
            customer=customer,
        )
        assert sale.total == variant.price * 2

    def test_insufficient_stock_raises(self, store, variant, customer):
        with pytest.raises(ValidationError):
            SaleService.create_sale(
                store=store,
                items=[{'variant': variant, 'quantity': 9999}],
                payment_type=Sale.PaymentType.CASH,
                customer=customer,
            )

    def test_debt_sale_creates_debt(self, store, variant, customer):
        sale = SaleService.create_sale(
            store=store,
            items=[{'variant': variant, 'quantity': 1}],
            payment_type=Sale.PaymentType.DEBT,
            customer=customer,
        )
        debt = Debt.objects.filter(
            customer=customer,
            store=store
        ).first()
        assert debt is not None
        assert debt.amount == sale.total
        assert debt.is_closed is False

    def test_debt_sale_without_customer_raises(self, store, variant):
        with pytest.raises(ValidationError):
            SaleService.create_sale(
                store=store,
                items=[{'variant': variant, 'quantity': 1}],
                payment_type=Sale.PaymentType.DEBT,
                customer=None,
            )

    def test_sale_saves_price_at_time_of_sale(self, store, variant, customer):
        original_price = variant.price
        sale = SaleService.create_sale(
            store=store,
            items=[{'variant': variant, 'quantity': 1}],
            payment_type=Sale.PaymentType.CASH,
            customer=customer,
        )
        variant.price = 99999
        variant.save()
        item = sale.items.first()
        assert item.price == original_price