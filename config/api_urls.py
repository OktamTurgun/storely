from django.urls import path
from apps.stores.views import StoreListCreateView, StoreDetailView
from apps.customers.views import CustomerListCreateView, CustomerDetailView
from apps.inventory.views import (
    CategoryListView, ProductListCreateView, ProductDetailView,
    ProductVariantListCreateView, ProductVariantDetailView,  # ← yangi
    RestockView, LowStockView
)
from apps.sales.views import SaleListView, SaleCreateView, SaleDetailView
from apps.debts.views import DebtListView, DebtPayView
from apps.reports.views import TodaySummaryView, MonthlySummaryView

urlpatterns = [
    # Stores
    path('stores/', StoreListCreateView.as_view()),
    path('stores/<uuid:pk>/', StoreDetailView.as_view()),

    # Customers
    path('stores/<uuid:store_id>/customers/', CustomerListCreateView.as_view()),
    path('stores/<uuid:store_id>/customers/<uuid:pk>/', CustomerDetailView.as_view()),

    # Inventory
    path('categories/', CategoryListView.as_view()),
    path('stores/<uuid:store_id>/products/', ProductListCreateView.as_view()),
    path('stores/<uuid:store_id>/products/<uuid:pk>/', ProductDetailView.as_view()),
    path('stores/<uuid:store_id>/products/low-stock/', LowStockView.as_view()),

    # Variants  ← yangi
    path('stores/<uuid:store_id>/products/<uuid:product_id>/variants/', ProductVariantListCreateView.as_view()),
    path('variants/<uuid:pk>/', ProductVariantDetailView.as_view()),
    path('variants/restock/', RestockView.as_view()),

    # Sales
    path('stores/<uuid:store_id>/sales/', SaleListView.as_view()),
    path('stores/sales/create/', SaleCreateView.as_view()),
    path('sales/<uuid:pk>/', SaleDetailView.as_view()),

    # Debts
    path('stores/<uuid:store_id>/debts/', DebtListView.as_view()),
    path('debts/<uuid:pk>/pay/', DebtPayView.as_view()),

    # Reports
    path('stores/<uuid:store_id>/reports/today/', TodaySummaryView.as_view()),
    path('stores/<uuid:store_id>/reports/monthly/', MonthlySummaryView.as_view()),
]