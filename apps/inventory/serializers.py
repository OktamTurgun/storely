from rest_framework import serializers
from .models import Category, Product, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id']


class ProductVariantSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'name', 'price',
            'quantity', 'min_threshold', 'image',
            'is_low_stock', 'created_at'
        ]
        read_only_fields = ['id', 'is_low_stock', 'created_at']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Narx musbat bo'lishi kerak.")
        return value

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Miqdor manfiy bo'lmaydi.")
        return value


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'store', 'category', 'category_name',
            'parent', 'name', 'image', 'variants', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'category_name']

    def validate_store(self, store):
        user = self.context['request'].user
        if store.owner != user:
            raise serializers.ValidationError(
                "Bu do'kon sizga tegishli emas."
            )
        return store


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    variant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'category_name', 'image', 'variant_count']


class RestockSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)