import pytest
import uuid
from apps.inventory.models import ProductVariant


@pytest.mark.django_db
class TestProductVariant:

    def test_is_low_stock_true(self, low_variant):
        assert low_variant.is_low_stock is True

    def test_is_low_stock_false(self, variant):
        assert variant.is_low_stock is False

    def test_soft_delete(self, variant):
        variant.delete()
        assert variant.is_deleted is True
        assert ProductVariant.objects.filter(id=variant.id).exists()

    def test_uuid_primary_key(self, variant):
        assert isinstance(variant.id, uuid.UUID)

    def test_str(self, variant):
        assert str(variant) == "Pepsi — 1L"