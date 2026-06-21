from celery import shared_task
from django.db.models import F

from apps.notifications.telegram import send_telegram_message


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_low_stock_all_stores(self):
    """Har kuni 08:00 — kam qolgan mahsulotlarni tekshir."""
    from apps.stores.models import Store
    from apps.inventory.models import ProductVariant

    stores = Store.objects.filter(is_deleted=False)

    for store in stores:
        low_variants = ProductVariant.objects.filter(
            product__store=store,
            product__is_deleted=False,
            is_deleted=False,
            quantity__lte=F('min_threshold'),
        ).select_related('product')

        if low_variants.exists():
            try:
                notify_low_stock.delay(
                    store_id=str(store.id),
                    variants=[
                        {
                            'name': f"{v.product.name} — {v.name}",
                            'quantity': v.quantity,
                            'min_threshold': v.min_threshold,
                        }
                        for v in low_variants
                    ],
                )
            except Exception as exc:
                self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_daily_report_all_stores(self):
    """Har kuni 20:00 — barcha do'konlarga hisobot."""
    from apps.stores.models import Store

    stores = Store.objects.filter(is_deleted=False)

    for store in stores:
        try:
            send_daily_report.delay(store_id=str(store.id))
        except Exception as exc:
            self.retry(exc=exc)


@shared_task
def notify_low_stock(store_id, variants):
    """Bitta do'kon uchun kam qolgan mahsulotlar xabari."""
    from apps.stores.models import Store

    store = Store.objects.select_related('owner').get(id=store_id)
    chat_id = store.owner.telegram_id

    lines = [f"⚠️ *{store.name}* — kam qolgan mahsulotlar:\n"]
    for v in variants:
        lines.append(
            f"• {v['name']}: {v['quantity']} dona qoldi "
            f"(chegara: {v['min_threshold']})"
        )

    send_telegram_message(chat_id, "\n".join(lines))


@shared_task
def send_daily_report(store_id):
    """Bitta do'kon uchun kunlik hisobot."""
    from apps.stores.models import Store
    from apps.reports.services import ReportService

    store = Store.objects.select_related('owner').get(id=store_id)
    chat_id = store.owner.telegram_id
    data = ReportService.today_summary(store)

    lines = [
        f"📊 *{store.name}* — bugungi hisobot\n",
        f"💰 Umumiy sotuv: {data['total_revenue']:,} so'm",
        f"📦 Jami sotuvlar: {data['total_sales']} ta\n",
        "🏆 Top mahsulotlar:",
    ]
    for p in data['top_products']:
        lines.append(
            f"  • {p['name']}: {p['total_qty']} dona "
            f"— {p['total_sum']:,} so'm"
        )

    send_telegram_message(chat_id, "\n".join(lines))
