from django.db.models import Sum, Count, F
from django.utils import timezone
from apps.sales.models import Sale, SaleItem


class ReportService:

    @staticmethod
    def today_summary(store):
        today = timezone.now().date()

        sales = Sale.objects.filter(
            store=store,
            sold_at__date=today,
        )
        total = sales.aggregate(Sum('total'))['total__sum'] or 0
        count = sales.count()

        top_products = SaleItem.objects.filter(
            sale__store=store,
            sale__sold_at__date=today,
        ).values(
            name=F('variant__product__name')
        ).annotate(
            total_qty=Sum('quantity'),
            total_sum=Sum(F('quantity') * F('price')),
        ).order_by('-total_qty')[:5]

        return {
            'date': today,
            'total_revenue': total,
            'total_sales': count,
            'top_products': list(top_products),
        }

    @staticmethod
    def monthly_summary(store, year, month):
        sales = Sale.objects.filter(
            store=store,
            sold_at__year=year,
            sold_at__month=month,
        )
        return {
            'total_revenue': sales.aggregate(
                Sum('total')
            )['total__sum'] or 0,
            'total_sales': sales.count(),
            'by_payment': list(
                sales.values('payment_type').annotate(
                    total=Sum('total'),
                    count=Count('id'),
                )
            ),
        }