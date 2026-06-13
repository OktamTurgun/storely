from rest_framework import serializers
from .models import Store


class StoreSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Store
        fields = ['id', 'owner', 'name', 'category', 'phone', 'address', 'created_at']
        read_only_fields = ['id', 'created_at']


class StoreListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'category', 'phone']