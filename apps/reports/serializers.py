from rest_framework import serializers


class TopProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    total_qty = serializers.IntegerField()
    total_sum = serializers.DecimalField(max_digits=12, decimal_places=2)


class TodaySummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_sales = serializers.IntegerField()
    top_products = TopProductSerializer(many=True)


class MonthlySummarySerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_sales = serializers.IntegerField()
    by_payment = serializers.ListField()