import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestSaleViews:

    def test_sale_list_returns_200(self, api_client, store):
        response = api_client.get(
            f'/api/v1/stores/{store.id}/sales/'
        )
        assert response.status_code == 200

    def test_sale_create_cash(self, api_client, store, variant, customer):
        payload = {
            'store_id': str(store.id),
            'customer_id': str(customer.id),
            'payment_type': 'cash',
            'items': [
                {'variant_id': str(variant.id), 'quantity': 2}
            ]
        }
        response = api_client.post(
            '/api/v1/stores/sales/create/',
            payload,
            format='json'
        )
        assert response.status_code == 201
        # Decimal formatini to'g'ri solishtirish
        assert Decimal(response.data['total']) == variant.price * 2

    def test_unauthorized_returns_401(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.get('/api/v1/stores/')
        # Django REST framework 403 yoki 401 qaytarishi mumkin
        assert response.status_code in [401, 403]

    def test_other_user_cannot_access_store(self, db, store):
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            username='other',
            password='pass'
        )
        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get(
            f'/api/v1/stores/{store.id}/sales/'
        )
        # Boshqa user faqat o'z do'konini ko'ra oladi
        # Bo'sh list qaytarishi kerak, chunki filter owner ga qarab ishlaydi
        assert response.status_code == 200
        assert response.data == []

    def test_low_stock_endpoint(self, api_client, store, low_variant):
        response = api_client.get(
            f'/api/v1/stores/{store.id}/products/low-stock/'
        )
        assert response.status_code == 200
        ids = [item['id'] for item in response.data]
        assert str(low_variant.id) in ids