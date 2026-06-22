import os
import tempfile
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from apps.bot.services.vision import recognize_product
from apps.inventory.models import ProductVariant

router = Router()


class ImageSaleState(StatesGroup):
    waiting_variant = State()
    waiting_quantity = State()


@router.message(F.photo)
async def image_handler(message: Message, bot: Bot, state: FSMContext, user):
    await message.answer("🖼 Rasm qabul qilindi, tahlil qilinmoqda...")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        await bot.download_file(file.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        from apps.stores.models import Store
        store = await sync_to_async(
            Store.objects.filter(owner=user, is_deleted=False).first
        )()

        if not store:
            await message.answer("Do'koningiz topilmadi.")
            return

        product_names = await sync_to_async(
            lambda: list(
                ProductVariant.objects.filter(
                    product__store=store,
                    product__is_deleted=False,
                    is_deleted=False,
                ).values_list('product__name', flat=True).distinct()
            )
        )()

        if not product_names:
            await message.answer(
                "Do'koningizda mahsulotlar yo'q.\n"
                "Avval mahsulot qo'shing."
            )
            return

        result = await recognize_product(tmp_path, product_names)

        if not result or not result.get('product_name'):
            await message.answer(
                "❌ Mahsulotni tanib bo'lmadi.\n"
                "Aniqroq rasm yuboring."
            )
            return

        variants = await sync_to_async(
            lambda: list(
                ProductVariant.objects.filter(
                    product__store=store,
                    product__name__iexact=result['product_name'],
                    is_deleted=False,
                ).select_related('product')
            )
        )()

        if not variants:
            await message.answer(
                f"Mahsulot topildi: *{result['product_name']}*\n"
                f"Lekin omborda variant yo'q."
            )
            return

        confidence_icon = "✅" if result['confidence'] == 'high' else "⚠️"

        if len(variants) == 1:
            variant = variants[0]
            await message.answer(
                f"{confidence_icon} *{variant.product.name} — {variant.name}*\n"
                f"_{result.get('description', '')}_\n\n"
                f"Omborda: *{variant.quantity}* dona\n"
                f"Narxi: *{variant.price:,}* so'm\n\n"
                f"Nechta sotildi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="1", callback_data="qty_1"),
                        InlineKeyboardButton(text="2", callback_data="qty_2"),
                        InlineKeyboardButton(text="5", callback_data="qty_5"),
                        InlineKeyboardButton(text="10", callback_data="qty_10"),
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Bekor qilish",
                            callback_data="qty_cancel"
                        )
                    ]
                ])
            )

            await state.set_state(ImageSaleState.waiting_quantity)
            await state.update_data(
                variant_id=str(variant.id),
                store_id=str(store.id),
            )
        else:
            buttons = []
            for v in variants:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{v.name} | {v.price:,} so'm | {v.quantity} ta",
                        callback_data=f"img_variant_{v.id}"
                    )
                ])
            buttons.append([
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="qty_cancel")
            ])
            await message.answer(
                f"{confidence_icon} Mahsulot topildi: *{variants[0].product.name}*\n"
                f"_{result.get('description', '')}_\n\n"
                f"Qaysi variantni tanlaysiz?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
            await state.set_state(ImageSaleState.waiting_variant)
            await state.update_data(
                store_id=str(store.id),
                description=result.get('description', ''),
                confidence_icon=confidence_icon,
            )

    finally:
        os.unlink(tmp_path)


@router.callback_query(ImageSaleState.waiting_variant, F.data.startswith('img_variant_'))
async def image_variant_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("img_variant_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    data = await state.get_data()
    await state.update_data(variant_id=variant_id)
    await state.set_state(ImageSaleState.waiting_quantity)

    await callback.message.edit_text(
        f"{data.get('confidence_icon', '')} *{variant.product.name} — {variant.name}*\n"
        f"_{data.get('description', '')}_\n\n"
        f"Omborda: *{variant.quantity}* dona\n"
        f"Narxi: *{variant.price:,}* so'm\n\n"
        f"Nechta sotildi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="qty_1"),
                InlineKeyboardButton(text="2", callback_data="qty_2"),
                InlineKeyboardButton(text="5", callback_data="qty_5"),
                InlineKeyboardButton(text="10", callback_data="qty_10"),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="qty_cancel"
                )
            ]
        ])
    )



@router.callback_query(ImageSaleState.waiting_quantity, F.data.startswith('qty_'))
async def quantity_chosen(callback: CallbackQuery, state: FSMContext, user):
    if callback.data == 'qty_cancel':
        await state.clear()
        await callback.message.edit_text("❌ Bekor qilindi.")
        return

    quantity = int(callback.data.split('_')[1])
    data = await state.get_data()

    variant = await sync_to_async(
        ProductVariant.objects.select_related('product').get
    )(id=data['variant_id'])

    from apps.stores.models import Store
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])

    from apps.sales.services import SaleService
    from apps.sales.models import Sale
    from django.core.exceptions import ValidationError

    try:
        await sync_to_async(SaleService.create_sale)(
            store=store,
            items=[{'variant': variant, 'quantity': quantity}],
            payment_type=Sale.PaymentType.CASH,
        )
        await callback.message.edit_text(
            f"✅ *Sotuv qayd etildi!*\n\n"
            f"📦 {variant.product.name} — {variant.name}\n"
            f"🔢 Miqdor: *{quantity}* dona\n"
            f"💰 Summa: *{variant.price * quantity:,}* so'm"
        )
    except ValidationError as e:
        await callback.message.edit_text(f"❌ Xato: {e.message}")

    await state.clear()