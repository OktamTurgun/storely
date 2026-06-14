import pytest
from django.core.exceptions import ValidationError
from apps.debts.models import Debt
from apps.debts.services import DebtService


@pytest.fixture
def debt(db, customer, store):
    return Debt.objects.create(
        customer=customer,
        store=store,
        amount=100_000,
    )


@pytest.mark.django_db
class TestDebtService:

    def test_partial_payment(self, debt):
        DebtService.pay_debt(debt, 40_000)
        debt.refresh_from_db()
        assert debt.paid == 40_000
        assert debt.remaining == 60_000
        assert debt.is_closed is False

    def test_full_payment_closes_debt(self, debt):
        DebtService.pay_debt(debt, 100_000)
        debt.refresh_from_db()
        assert debt.is_closed is True

    def test_overpayment_raises(self, debt):
        with pytest.raises(ValidationError):
            DebtService.pay_debt(debt, 200_000)

    def test_zero_payment_raises(self, debt):
        with pytest.raises(ValidationError):
            DebtService.pay_debt(debt, 0)