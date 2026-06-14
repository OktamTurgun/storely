import pytest
from django.contrib.auth import get_user_model
from apps.stores.models import Store
from apps.inventory.models import Category, Product, ProductVariant
from apps.customers.models import Customer

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
    )


@pytest.fixture
def store(db, user):
    return Store.objects.create(
        owner=user,
        name="Test Do'kon",
        category=Store.Category.GROCERY,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(
        name='Ichimliklar',
        slug='ichimliklar',
    )


@pytest.fixture
def product(db, store, category):
    return Product.objects.create(
        store=store,
        category=category,
        name='Pepsi',
    )


@pytest.fixture
def variant(db, product):
    return ProductVariant.objects.create(
        product=product,
        name='1L',
        price=8000,
        quantity=50,
        min_threshold=5,
    )


@pytest.fixture
def low_variant(db, product):
    return ProductVariant.objects.create(
        product=product,
        name='0.5L',
        price=5000,
        quantity=3,
        min_threshold=5,
    )


@pytest.fixture
def customer(db, store):
    return Customer.objects.create(
        store=store,
        name='Sardor aka',
        phone='+998901234567',
    )


@pytest.fixture
def api_client(user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=user)
    return client