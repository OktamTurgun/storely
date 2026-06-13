from aiogram import Router, F
from aiogram.types import Message
from asgiref.sync import sync_to_async
from apps.reports.services import ReportService
from apps.stores.models import Store

router = Router()


@router.message(F.text == "📊 Bugungi hisobot")
async def today_report(message: Message, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    data = await sync_to_async(ReportService.today_summary)(store)

    top = "\n".join(
        f"  • {p['name']}: {p['total_qty']} dona — "
        f"{p['total_sum']:,} so'm"
        for p in data['top_products']
    ) or "  Sotuvlar yo'q"

    await message.answer(
        f"📊 *Bugungi hisobot*\n\n"
        f"💰 Umumiy sotuv: *{data['total_revenue']:,} so'm*\n"
        f"📦 Jami sotuvlar: *{data['total_sales']} ta*\n\n"
        f"🏆 *Top mahsulotlar:*\n{top}"
    )


@router.message(F.text == "⚠️ Kam qolganlar")
async def low_stock(message: Message, user):
    from apps.inventory.services import ProductService

    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    variants = await sync_to_async(
        lambda: list(
            ProductService.get_low_stock(store)
            .select_related('product')
        )
    )()

    if not variants:
        await message.answer("✅ Barcha mahsulotlar yetarli!")
        return

    lines = ["⚠️ *Kam qolgan mahsulotlar:*\n"]
    for v in variants:
        lines.append(
            f"• {v.product.name} — {v.name}: "
            f"*{v.quantity}* dona qoldi "
            f"(min: {v.min_threshold})"
        )

    await message.answer("\n".join(lines))