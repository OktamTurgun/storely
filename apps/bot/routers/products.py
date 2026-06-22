"""
Mahsulotlar boshqaruvi routeri.
Bot ichidan mahsulot qo'shish, ko'rish, tahrirlash, o'chirish.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.stores.models import Store
from apps.inventory.models import Product, ProductVariant, Category
from apps.inventory.services import ProductService

router = Router()

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class AddProductState(StatesGroup):
    waiting_name = State()
    waiting_variant_name = State()
    waiting_price = State()
    waiting_quantity = State()
    waiting_threshold = State()


class EditProductState(StatesGroup):
    choosing_product = State()
    choosing_field = State()
    waiting_value = State()


class DeleteProductState(StatesGroup):
    choosing_product = State()
    confirming = State()


# ---------------------------------------------------------------------------
# Helper keyboards
# ---------------------------------------------------------------------------

def product_list_keyboard(variants, page=0, page_size=8, action="edit"):
    """Variant tanlov klaviaturasi. action: 'edit' | 'delete'"""
    start = page * page_size
    page_variants = variants[start:start + page_size]
    buttons = []
    for v in page_variants:
        cb = f"{action}_v_{v.id}"
        buttons.append([InlineKeyboardButton(
            text=f"📦 {v.product.name} — {v.name} | {v.price:,} so'm | {v.quantity} dona",
            callback_data=cb
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{action}_page_{page - 1}"))
    if start + page_size < len(variants):
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{action}_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="prod_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_field_keyboard(variant_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Nomini", callback_data=f"ef_name_{variant_id}"),
            InlineKeyboardButton(text="💰 Narxini", callback_data=f"ef_price_{variant_id}"),
        ],
        [
            InlineKeyboardButton(text="📊 Miqdorini", callback_data=f"ef_qty_{variant_id}"),
            InlineKeyboardButton(text="⚠️ Min chegara", callback_data=f"ef_thr_{variant_id}"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="prod_back")],
    ])


# ---------------------------------------------------------------------------
# Entry point: "🗂 Mahsulotlar" tugmasi
# ---------------------------------------------------------------------------

@router.message(F.text == "🗂 Mahsulotlar")
async def products_main(message: Message, state: FSMContext):
    await state.clear()
    from apps.bot.keyboards.main import products_menu
    await message.answer(
        "🗂 *Mahsulotlar boshqaruvi*\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=products_menu(),
    )


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "prod_list")
async def prod_list(callback: CallbackQuery, state: FSMContext, user):
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
            "📦 Hali mahsulot qo'shilmagan.\n\n"
            "➕ *Qo'shish* tugmasi orqali birinchi mahsulotingizni kiriting.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="prod_add")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
            ])
        )
        return

    lines = [f"📋 *Mahsulotlar ro'yxati* ({len(variants)} ta):\n"]
    for v in variants:
        stock_icon = "⚠️" if v.is_low_stock else "✅"
        lines.append(
            f"{stock_icon} *{v.product.name}* — {v.name}\n"
            f"   💰 {v.price:,} so'm | 📦 {v.quantity} dona"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Qo'shish", callback_data="prod_add")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
        ])
    )


# ---------------------------------------------------------------------------
# ADD PRODUCT
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "prod_add")
async def prod_add_start(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await callback.message.edit_text("Do'koningiz topilmadi.")
        return

    await state.update_data(store_id=str(store.id))
    await state.set_state(AddProductState.waiting_name)
    await callback.message.edit_text(
        "➕ *Yangi mahsulot qo'shish*\n\n"
        "📝 Mahsulot *nomini* kiriting:\n"
        "_Masalan: Non, Guruch, Shakar_"
    )


@router.message(AddProductState.waiting_name)
async def prod_add_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Nom kamida 2 ta harf bo'lishi kerak.")
        return
    await state.update_data(product_name=name)
    await state.set_state(AddProductState.waiting_variant_name)
    await message.answer(
        f"✅ Mahsulot: *{name}*\n\n"
        "📦 Variant *nomini* kiriting:\n"
        "_Masalan: 1 kg, 500g, Katta, Kichik_\n\n"
        "_(Faqat bitta tur bo'lsa \"Standart\" deb yozing)_"
    )


@router.message(AddProductState.waiting_variant_name)
async def prod_add_variant_name(message: Message, state: FSMContext):
    variant_name = message.text.strip()
    if len(variant_name) < 1:
        await message.answer("❌ Variant nomi kiritilmadi.")
        return
    await state.update_data(variant_name=variant_name)
    await state.set_state(AddProductState.waiting_price)
    await message.answer(
        f"✅ Variant: *{variant_name}*\n\n"
        "💰 *Narxini* kiriting (so'mda):\n"
        "_Masalan: 5000_"
    )


@router.message(AddProductState.waiting_price)
async def prod_add_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(' ', '').replace(',', ''))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Narxni to'g'ri kiriting. Masalan: 5000")
        return
    await state.update_data(price=price)
    await state.set_state(AddProductState.waiting_quantity)
    await message.answer(
        f"✅ Narx: *{price:,.0f} so'm*\n\n"
        "📊 *Boshlang'ich miqdorini* kiriting (dona):\n"
        "_Masalan: 50_"
    )


@router.message(AddProductState.waiting_quantity)
async def prod_add_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Miqdorni to'g'ri kiriting. Masalan: 50")
        return
    await state.update_data(quantity=quantity)
    await state.set_state(AddProductState.waiting_threshold)
    await message.answer(
        f"✅ Miqdor: *{quantity}* dona\n\n"
        "⚠️ *Minimal chegara* kiriting (shu miqdordan kam qolganda ogohlantiradi):\n"
        "_Masalan: 5_\n\n"
        "_O'tkazib yuborish uchun 0 yozing_"
    )


@router.message(AddProductState.waiting_threshold)
async def prod_add_threshold(message: Message, state: FSMContext):
    try:
        threshold = int(message.text.strip())
        if threshold < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ To'g'ri raqam kiriting. Masalan: 5")
        return

    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])

    # Default category: "Umumiy"
    category = await sync_to_async(
        lambda: Category.objects.get_or_create(name="Umumiy", defaults={"slug": "umumiy"})[0]
    )()

    try:
        product = await sync_to_async(ProductService.create_product)(
            store=store,
            name=data['product_name'],
            category=category,
        )
        variant = await sync_to_async(ProductService.create_variant)(
            product=product,
            name=data['variant_name'],
            price=data['price'],
            quantity=data['quantity'],
            min_threshold=threshold or 5,
        )

        await message.answer(
            f"🎉 *Mahsulot muvaffaqiyatli qo'shildi!*\n\n"
            f"📦 *{product.name}* — {variant.name}\n"
            f"💰 Narxi: *{variant.price:,} so'm*\n"
            f"📊 Miqdor: *{variant.quantity}* dona\n"
            f"⚠️ Min chegara: *{variant.min_threshold}* dona",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Yana qo'shish", callback_data="prod_add")],
                [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="prod_list")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
            ])
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")

    await state.clear()


# ---------------------------------------------------------------------------
# EDIT PRODUCT
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "prod_edit")
async def prod_edit_start(callback: CallbackQuery, state: FSMContext, user):
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
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
            ])
        )
        return

    await state.update_data(store_id=str(store.id), edit_page=0)
    await state.set_state(EditProductState.choosing_product)
    await callback.message.edit_text(
        "✏️ *Qaysi mahsulotni tahrirlaysiz?*",
        reply_markup=product_list_keyboard(variants, page=0, action="edit")
    )


@router.callback_query(EditProductState.choosing_product, F.data.startswith("edit_page_"))
async def prod_edit_page(callback: CallbackQuery, state: FSMContext, user):
    page = int(callback.data.replace("edit_page_", ""))
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    variants = await sync_to_async(
        lambda: list(
            ProductVariant.objects.filter(
                product__store=store, is_deleted=False
            ).select_related('product').order_by('product__name', 'name')
        )
    )()
    await state.update_data(edit_page=page)
    await callback.message.edit_reply_markup(
        reply_markup=product_list_keyboard(variants, page=page, action="edit")
    )


@router.callback_query(EditProductState.choosing_product, F.data.startswith("edit_v_"))
async def prod_edit_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("edit_v_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    await state.update_data(edit_variant_id=variant_id)
    await state.set_state(EditProductState.choosing_field)
    await callback.message.edit_text(
        f"✏️ *{variant.product.name} — {variant.name}*\n"
        f"💰 Narxi: *{variant.price:,} so'm*\n"
        f"📊 Miqdor: *{variant.quantity}* dona\n"
        f"⚠️ Min chegara: *{variant.min_threshold}* dona\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=edit_field_keyboard(variant_id)
    )


@router.callback_query(EditProductState.choosing_field, F.data.startswith("ef_"))
async def prod_edit_field(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # ef_name_<id>, ef_price_<id>, ef_qty_<id>, ef_thr_<id>
    field = parts[1]
    variant_id = "_".join(parts[2:])

    field_map = {
        "name": ("📝 Yangi variant nomini kiriting:", "variant_name"),
        "price": ("💰 Yangi narxni kiriting (so'm):", "price"),
        "qty": ("📊 Yangi miqdorni kiriting (dona):", "quantity"),
        "thr": ("⚠️ Yangi minimal chegara kiriting (dona):", "threshold"),
    }

    prompt, field_key = field_map.get(field, ("?", "?"))
    await state.update_data(edit_field=field_key, edit_variant_id=variant_id)
    await state.set_state(EditProductState.waiting_value)
    await callback.message.edit_text(prompt)


@router.message(EditProductState.waiting_value)
async def prod_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data['edit_field']
    variant_id = data['edit_variant_id']
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()

    try:
        if field == "variant_name":
            variant.name = message.text.strip()
            await sync_to_async(variant.save)(update_fields=['name', 'updated_at'])
            result = f"📝 Yangi nom: *{variant.name}*"
        elif field == "price":
            price = float(message.text.replace(' ', '').replace(',', ''))
            if price <= 0:
                raise ValueError
            variant.price = price
            await sync_to_async(variant.save)(update_fields=['price', 'updated_at'])
            result = f"💰 Yangi narx: *{price:,.0f} so'm*"
        elif field == "quantity":
            qty = int(message.text.strip())
            if qty < 0:
                raise ValueError
            variant.quantity = qty
            await sync_to_async(variant.save)(update_fields=['quantity', 'updated_at'])
            result = f"📊 Yangi miqdor: *{qty}* dona"
        elif field == "threshold":
            thr = int(message.text.strip())
            if thr < 0:
                raise ValueError
            variant.min_threshold = thr
            await sync_to_async(variant.save)(update_fields=['min_threshold', 'updated_at'])
            result = f"⚠️ Yangi chegara: *{thr}* dona"
        else:
            result = "O'zgarishlar saqlandi."

        await message.answer(
            f"✅ *{variant.product.name} — {variant.name}*\n"
            f"{result}\n\n"
            f"Muvaffaqiyatli yangilandi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Yana tahrirlash", callback_data="prod_edit")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
            ])
        )
    except (ValueError, TypeError):
        await message.answer("❌ Noto'g'ri qiymat. Qaytadan kiriting:")
        return

    await state.clear()


# ---------------------------------------------------------------------------
# DELETE PRODUCT
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "prod_delete")
async def prod_delete_start(callback: CallbackQuery, state: FSMContext, user):
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
            "📦 O'chirish uchun mahsulot yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
            ])
        )
        return

    await state.update_data(store_id=str(store.id))
    await state.set_state(DeleteProductState.choosing_product)
    await callback.message.edit_text(
        "🗑 *Qaysi mahsulotni o'chirmoqchisiz?*\n\n"
        "⚠️ O'chirilgan mahsulot tiklash imkoni yo'q!",
        reply_markup=product_list_keyboard(variants, page=0, action="delete")
    )


@router.callback_query(DeleteProductState.choosing_product, F.data.startswith("delete_page_"))
async def prod_delete_page(callback: CallbackQuery, state: FSMContext, user):
    page = int(callback.data.replace("delete_page_", ""))
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    variants = await sync_to_async(
        lambda: list(
            ProductVariant.objects.filter(
                product__store=store, is_deleted=False
            ).select_related('product').order_by('product__name', 'name')
        )
    )()
    await callback.message.edit_reply_markup(
        reply_markup=product_list_keyboard(variants, page=page, action="delete")
    )


@router.callback_query(DeleteProductState.choosing_product, F.data.startswith("delete_v_"))
async def prod_delete_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("delete_v_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    await state.update_data(delete_variant_id=variant_id)
    await state.set_state(DeleteProductState.confirming)
    await callback.message.edit_text(
        f"🗑 *O'chirishni tasdiqlaysizmi?*\n\n"
        f"📦 *{variant.product.name} — {variant.name}*\n"
        f"💰 Narxi: *{variant.price:,} so'm*\n"
        f"📊 Miqdor: *{variant.quantity}* dona\n\n"
        f"⚠️ Bu amalni bekor qilib bo'lmaydi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data="delete_confirm_yes"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="prod_back"),
            ]
        ])
    )


@router.callback_query(DeleteProductState.confirming, F.data == "delete_confirm_yes")
async def prod_delete_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['delete_variant_id'])
    )()

    product_name = variant.product.name
    variant_name = variant.name

    # Soft delete
    variant.is_deleted = True
    await sync_to_async(variant.save)(update_fields=['is_deleted', 'updated_at'])

    # Agar productning barcha variantlari o'chirilgan bo'lsa, productni ham o'chirish
    remaining = await sync_to_async(
        lambda: ProductVariant.objects.filter(
            product=variant.product, is_deleted=False
        ).count()
    )()
    if remaining == 0:
        product = variant.product
        product.is_deleted = True
        await sync_to_async(product.save)(update_fields=['is_deleted', 'updated_at'])

    await callback.message.edit_text(
        f"✅ *{product_name} — {variant_name}* o'chirildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="prod_list")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
        ])
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Shared "back" handlers
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "prod_back")
async def prod_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from apps.bot.keyboards.main import products_menu
    await callback.message.edit_text(
        "🗂 *Mahsulotlar boshqaruvi*\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=products_menu(),
    )


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
