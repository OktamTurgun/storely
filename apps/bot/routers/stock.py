from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from apps.stores.models import Store
from apps.inventory.models import ProductVariant
from apps.inventory.services import ProductService

router = Router()


class RestockState(StatesGroup):
    waiting_quantity = State()


def variants_keyboard(variants):
    buttons = []
    for v in variants:
        buttons.append([
            InlineKeyboardButton(
                text=f"{v.product.name} — {v.name} | {v.quantity} dona",
                callback_data=f"restock_variant_{v.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="restock_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quantity_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10", callback_data="rqty_10"),
            InlineKeyboardButton(text="20", callback_data="rqty_20"),
            InlineKeyboardButton(text="50", callback_data="rqty_50"),
            InlineKeyboardButton(text="100", callback_data="rqty_100"),
        ],
        [InlineKeyboardButton(text="✏️ Boshqa", callback_data="rqty_custom")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="restock_cancel")]
    ])


@router.message(F.text == "📥 Kirim")
async def restock_start(message: Message, state: FSMContext, user):
    await state.clear()

    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    variants = await sync_to_async(
        lambda: list(
            ProductVariant.objects.filter(
                product__store=store,
                is_deleted=False,
            ).select_related('product').order_by('product__name')[:20]
        )
    )()

    if not variants:
        await message.answer("⚠️ Hozircha mahsulot yo'q.")
        return

    await state.update_data(store_id=str(store.id))
    await message.answer(
        "📥 *Qaysi mahsulotga kirim?*\nQuyidagilardan tanlang:",
        reply_markup=variants_keyboard(variants)
    )


@router.callback_query(F.data.startswith("restock_variant_"))
async def restock_variant_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("restock_variant_", "")

    variant = await sync_to_async(
        ProductVariant.objects.select_related('product').get
    )(id=variant_id)

    await state.update_data(variant_id=variant_id)
    await state.set_state(RestockState.waiting_quantity)

    await callback.message.edit_text(
        f"📦 *{variant.product.name} — {variant.name}*\n"
        f"Hozir omborda: *{variant.quantity}* dona\n\n"
        f"Nechta keldi?",
        reply_markup=quantity_keyboard()
    )


@router.callback_query(RestockState.waiting_quantity, F.data.startswith("rqty_"))
async def restock_quantity_chosen(callback: CallbackQuery, state: FSMContext):
    if callback.data == "rqty_custom":
        await callback.message.edit_text("Miqdorni kiriting (raqam):")
        return

    quantity = int(callback.data.replace("rqty_", ""))
    data = await state.get_data()

    variant = await sync_to_async(
        ProductVariant.objects.select_related('product').get
    )(id=data['variant_id'])

    from django.core.exceptions import ValidationError
    try:
        await sync_to_async(ProductService.restock)(variant, quantity)
        await sync_to_async(variant.refresh_from_db)()
        await callback.message.edit_text(
            f"✅ *Kirim qayd etildi!*\n\n"
            f"📦 {variant.product.name} — {variant.name}\n"
            f"➕ Keldi: *{quantity}* dona\n"
            f"📊 Omborda jami: *{variant.quantity}* dona"
        )
    except ValidationError as e:
        await callback.message.edit_text(f"❌ Xato: {e.message}")

    await state.clear()


@router.message(RestockState.waiting_quantity)
async def restock_quantity_manual(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("Raqam kiriting.")
        return

    data = await state.get_data()
    variant = await sync_to_async(
        ProductVariant.objects.select_related('product').get
    )(id=data['variant_id'])

    from django.core.exceptions import ValidationError
    try:
        await sync_to_async(ProductService.restock)(variant, quantity)
        await sync_to_async(variant.refresh_from_db)()
        await message.answer(
            f"✅ *Kirim qayd etildi!*\n\n"
            f"📦 {variant.product.name} — {variant.name}\n"
            f"➕ Keldi: *{quantity}* dona\n"
            f"📊 Omborda jami: *{variant.quantity}* dona"
        )
    except ValidationError as e:
        await message.answer(f"❌ Xato: {e.message}")

    await state.clear()


@router.callback_query(F.data == "restock_cancel")
async def restock_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")