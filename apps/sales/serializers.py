from rest_framework import serializers
from .models import Sale, SaleItem


class SaleItemInputSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class SaleItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(
        source='variant.name',
        read_only=True
    )
    product_name = serializers.CharField(
        source='variant.product.name',
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = ['id', 'variant_name', 'product_name', 'quantity', 'price', 'subtotal']

    def get_subtotal(self, obj):
        return obj.get_subtotal()


class SaleCreateSerializer(serializers.Serializer):
    store_id = serializers.UUIDField()
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    payment_type = serializers.ChoiceField(choices=Sale.PaymentType.choices)
    items = SaleItemInputSerializer(many=True, min_length=1)

    def validate_items(self, items):
        ids = [i['variant_id'] for i in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Bir xil variant ikki marta kiritilgan."
            )
        return items


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(
        source='customer.name',
        read_only=True,
        default=None
    )
    payment_type_display = serializers.CharField(
        source='get_payment_type_display',
        read_only=True
    )

    class Meta:
        model = Sale
        fields = [
            'id', 'store', 'customer_name', 'payment_type',
            'payment_type_display', 'total', 'items', 'sold_at'
        ]
        read_only_fields = fields