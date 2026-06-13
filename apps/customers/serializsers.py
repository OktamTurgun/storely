from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    total_debt = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Customer
        fields = ['id', 'store', 'name', 'phone', 'note', 'total_debt', 'created_at']
        read_only_fields = ['id', 'created_at', 'total_debt']

    def validate_store(self, store):
        user = self.context['request'].user
        if store.owner != user:
            raise serializers.ValidationError(
                "Bu do'kon sizga tegishli emas."
            )
        return store


class CustomerListSerializer(serializers.ModelSerializer):
    total_debt = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'total_debt']