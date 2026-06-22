"""
Do'kon sozlamalari routeri.
Bot ichidan do'kon nomini, minimal chegara sozlash.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.stores.models import Store
from apps.inventory.models import ProductVariant

router = Router()


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class SettingsState(StatesGroup):
    waiting_store_name = State()
    waiting_threshold_product = State()
    waiting_threshold_value = State()


# ---------------------------------------------------------------------------
# Entry point: "⚙️ Sozlamalar" tugmasi
# ---------------------------------------------------------------------------

@router.message(F.text == "⚙️ Sozlamalar")
async def settings_main(message: Message, state: FSMContext, user):
    await state.clear()

    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    from apps.bot.keyboards.main import settings_menu
    await message.answer(
        f"⚙️ *Sozlamalar*\n\n"
        f"🏪 Do'kon: *{store.name}*\n"
        f"👤 Egasi: *{user.get_full_name() or user.username}*\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=settings_menu(),
    )


# ---------------------------------------------------------------------------
# Store name change
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "set_store_name")
async def set_store_name_start(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    await state.update_data(store_id=str(store.id))
    await state.set_state(SettingsState.waiting_store_name)
    await callback.message.edit_text(
        f"🏪 *Do'kon nomini o'zgartirish*\n\n"
        f"Hozirgi nom: *{store.name}*\n\n"
        f"Yangi nomni kiriting:"
    )


@router.message(SettingsState.waiting_store_name)
async def set_store_name_value(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer("❌ Nom kamida 2 ta harf bo'lishi kerak.")
        return

    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    old_name = store.name
    store.name = new_name
    await sync_to_async(store.save)(update_fields=['name', 'updated_at'])

    await message.answer(
        f"✅ *Do'kon nomi o'zgartirildi!*\n\n"
        f"Eski nom: *{old_name}*\n"
        f"Yangi nom: *{new_name}*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Sozlamalarga qaytish", callback_data="settings_back")],
        ])
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Min threshold — all products bulk change
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "set_threshold")
async def set_threshold_start(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await callback.message.edit_text("Do'koningiz topilmadi.")
        return

    variants = await sync_to_async(
        lambda: list(
            ProductVariant.objects.filter(
                product__store=store, is_deleted=False
            ).select_related('product').order_by('product__name', 'name')
        )
    )()

    if not variants:
        await callback.message.edit_text(
            "📦 Hali mahsulot yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="settings_back")]
            ])
        )
        return

    await state.update_data(store_id=str(store.id))

    # Buttons: har bir variant uchun
    buttons = []
    for v in variants[:15]:
        buttons.append([InlineKeyboardButton(
            text=f"📦 {v.product.name} — {v.name} (hozir: {v.min_threshold})",
            callback_data=f"thr_v_{v.id}"
        )])
    buttons.append([InlineKeyboardButton(
        text="📊 Barchasini bir xil qilish",
        callback_data="thr_all"
    )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="settings_back")])

    await state.set_state(SettingsState.waiting_threshold_product)
    await callback.message.edit_text(
        "⚠️ *Minimal chegara sozlash*\n\n"
        "Qaysi mahsulotning chegarasini o'zgartirasiz?\n"
        "_(Bu chegara ostiga tushganda ogohlantirish keladi)_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(SettingsState.waiting_threshold_product, F.data.startswith("thr_v_"))
async def set_threshold_variant(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("thr_v_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    await state.update_data(threshold_variant_id=variant_id, threshold_mode="single")
    await state.set_state(SettingsState.waiting_threshold_value)
    await callback.message.edit_text(
        f"⚠️ *{variant.product.name} — {variant.name}*\n"
        f"Hozirgi chegara: *{variant.min_threshold}* dona\n\n"
        f"Yangi minimal chegarani kiriting:"
    )


@router.callback_query(SettingsState.waiting_threshold_product, F.data == "thr_all")
async def set_threshold_all(callback: CallbackQuery, state: FSMContext):
    await state.update_data(threshold_mode="all")
    await state.set_state(SettingsState.waiting_threshold_value)
    await callback.message.edit_text(
        "📊 *Barcha mahsulotlar uchun minimal chegara*\n\n"
        "Yangi minimal chegarani kiriting (barcha mahsulotlarga qo'llaniladi):"
    )


@router.message(SettingsState.waiting_threshold_value)
async def set_threshold_value(message: Message, state: FSMContext):
    try:
        threshold = int(message.text.strip())
        if threshold < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ To'g'ri raqam kiriting. Masalan: 5")
        return

    data = await state.get_data()
    mode = data.get('threshold_mode', 'single')

    if mode == "all":
        store = await sync_to_async(Store.objects.get)(id=data['store_id'])
        updated = await sync_to_async(
            lambda: ProductVariant.objects.filter(
                product__store=store, is_deleted=False
            ).update(min_threshold=threshold)
        )()
        await message.answer(
            f"✅ *{updated}* ta mahsulot uchun minimal chegara *{threshold}* dona qilib o'rnatildi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Sozlamalarga qaytish", callback_data="settings_back")],
            ])
        )
    else:
        variant = await sync_to_async(
            lambda: ProductVariant.objects.select_related('product').get(id=data['threshold_variant_id'])
        )()
        variant.min_threshold = threshold
        await sync_to_async(variant.save)(update_fields=['min_threshold', 'updated_at'])
        await message.answer(
            f"✅ *{variant.product.name} — {variant.name}*\n"
            f"Yangi chegara: *{threshold}* dona qilib belgilandi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Sozlamalarga qaytish", callback_data="settings_back")],
            ])
        )

    await state.clear()


# ---------------------------------------------------------------------------
# Back handler
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery, state: FSMContext, user):
    await state.clear()
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    from apps.bot.keyboards.main import settings_menu
    await callback.message.edit_text(
        f"⚙️ *Sozlamalar*\n\n"
        f"🏪 Do'kon: *{store.name if store else '?'}*\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=settings_menu(),
    )
