from rest_framework import serializers
from .models import Debt


class DebtSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.name',
        read_only=True
    )
    remaining = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Debt
        fields = [
            'id', 'customer_name', 'amount', 'paid',
            'remaining', 'is_closed', 'due_date', 'created_at'
        ]
        read_only_fields = ['id', 'remaining', 'is_closed', 'created_at']


class DebtPaySerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1
    )