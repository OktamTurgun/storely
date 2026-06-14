import pytest
from django.core.exceptions import ValidationError
from apps.inventory.services import ProductService


@pytest.mark.django_db
class TestProductService:

    def test_restock_increases_quantity(self, variant):
        original = variant.quantity
        ProductService.restock(variant, 10)
        variant.refresh_from_db()
        assert variant.quantity == original + 10

    def test_restock_zero_raises(self, variant):
        with pytest.raises(ValidationError):
            ProductService.restock(variant, 0)

    def test_restock_negative_raises(self, variant):
        with pytest.raises(ValidationError):
            ProductService.restock(variant, -5)

    def test_get_low_stock(self, store, low_variant, variant):
        low = list(ProductService.get_low_stock(store))
        ids = [v.id for v in low]
        assert low_variant.id in ids
        assert variant.id not in ids

    def test_create_variant_negative_price_raises(self, product):
        with pytest.raises(ValidationError):
            ProductService.create_variant(
                product=product,
                name='Test',
                price=-100,
                quantity=10,
            )

    def test_create_variant_negative_quantity_raises(self, product):
        with pytest.raises(ValidationError):
            ProductService.create_variant(
                product=product,
                name='Test',
                price=5000,
                quantity=-1,
            )