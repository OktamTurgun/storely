from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from .models import Category, Product, ProductVariant
from .serializers import (
    CategorySerializer, ProductSerializer, ProductListSerializer,
    ProductVariantSerializer, RestockSerializer
)
from .services import ProductService


class CategoryListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_deleted=False)


class ProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        return Product.objects.filter(
            store__owner=self.request.user,
            store_id=store_id,
            is_deleted=False,
            parent=None,
        ).annotate(
            variant_count=Count('variants')
        ).order_by('name')


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(
            store__owner=self.request.user,
            is_deleted=False,
        )

    def perform_destroy(self, instance):
        instance.delete()


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductVariantSerializer

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product__store__owner=self.request.user,
            is_deleted=False,
        )

    def perform_destroy(self, instance):
        instance.delete()


class RestockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            variant = ProductVariant.objects.get(
                id=serializer.validated_data['variant_id'],
                product__store__owner=request.user,
                is_deleted=False,
            )
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'Mahsulot topilmadi.'}, status=404)

        updated = ProductService.restock(
            variant,
            serializer.validated_data['quantity']
        )
        return Response(ProductVariantSerializer(updated).data)


class LowStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id):
        from apps.stores.models import Store
        try:
            store = Store.objects.get(
                id=store_id,
                owner=request.user,
                is_deleted=False,
            )
        except Store.DoesNotExist:
            return Response({'detail': "Do'kon topilmadi."}, status=404)

        variants = ProductService.get_low_stock(store)
        return Response(ProductVariantSerializer(variants, many=True).data)
