from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .models import Sale
from .serializers import SaleSerializer, SaleCreateSerializer
from .services import SaleService
from apps.stores.models import Store
from apps.inventory.models import ProductVariant
from apps.customers.models import Customer


class SaleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SaleSerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        return Sale.objects.filter(
            store__owner=self.request.user,
            store_id=store_id,
        ).prefetch_related('items__variant__product').order_by('-sold_at')


class SaleCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            store = Store.objects.get(
                id=data['store_id'],
                owner=request.user,
                is_deleted=False,
            )
        except Store.DoesNotExist:
            return Response({'detail': "Do'kon topilmadi."}, status=404)

        customer = None
        if data.get('customer_id'):
            try:
                customer = Customer.objects.get(
                    id=data['customer_id'],
                    store=store,
                    is_deleted=False,
                )
            except Customer.DoesNotExist:
                return Response({'detail': 'Mijoz topilmadi.'}, status=404)

        items = []
        for item in data['items']:
            try:
                variant = ProductVariant.objects.get(
                    id=item['variant_id'],
                    product__store=store,
                    is_deleted=False,
                )
                items.append({
                    'variant': variant,
                    'quantity': item['quantity']
                })
            except ProductVariant.DoesNotExist:
                return Response(
                    {'detail': f"Variant topilmadi."},
                    status=404
                )

        try:
            sale = SaleService.create_sale(
                store=store,
                items=items,
                payment_type=data['payment_type'],
                customer=customer,
            )
        except ValidationError as e:
            return Response({'detail': str(e.message)}, status=400)

        return Response(
            SaleSerializer(sale).data,
            status=status.HTTP_201_CREATED
        )


class SaleDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SaleSerializer

    def get_queryset(self):
        return Sale.objects.filter(
            store__owner=self.request.user,
        ).prefetch_related('items__variant__product')
