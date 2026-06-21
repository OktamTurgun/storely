from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from apps.stores.models import Store
from apps.inventory.models import ProductVariant
from apps.sales.services import SaleService
from apps.sales.models import Sale

router = Router()


class SaleState(StatesGroup):
    waiting_quantity     = State()
    waiting_payment      = State()
    waiting_customer     = State()
    waiting_new_customer = State()


def variants_keyboard(variants):
    buttons = []
    for v in variants:
        buttons.append([
            InlineKeyboardButton(
                text=f"{v.product.name} — {v.name} | {v.price:,} so'm | {v.quantity} dona",
                callback_data=f"sale_variant_{v.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sale_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Naqd", callback_data="pay_cash"),
            InlineKeyboardButton(text="💳 Karta", callback_data="pay_card"),
            InlineKeyboardButton(text="📋 Qarzga", callback_data="pay_debt"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sale_cancel")]
    ])


def quantity_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="qty_1"),
            InlineKeyboardButton(text="2", callback_data="qty_2"),
            InlineKeyboardButton(text="3", callback_data="qty_3"),
            InlineKeyboardButton(text="5", callback_data="qty_5"),
        ],
        [
            InlineKeyboardButton(text="10", callback_data="qty_10"),
            InlineKeyboardButton(text="20", callback_data="qty_20"),
            InlineKeyboardButton(text="50", callback_data="qty_50"),
            InlineKeyboardButton(text="✏️ Boshqa", callback_data="qty_custom"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sale_cancel")]
    ])


def customers_keyboard(customers):
    buttons = []
    for c in customers:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {c['name']}",
                callback_data=f"debt_customer_{c['id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi mijoz", callback_data="debt_new_customer")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sale_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.text == "📦 Sotuv")
async def sale_start(message: Message, state: FSMContext, user):
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
                quantity__gt=0,
            ).select_related('product').order_by('product__name')[:20]
        )
    )()

    if not variants:
        await message.answer("⚠️ Omborda mahsulot yo'q.")
        return

    await state.update_data(store_id=str(store.id))
    await message.answer(
        "📦 *Qaysi mahsulot sotildi?*\nQuyidagilardan tanlang:",
        reply_markup=variants_keyboard(variants)
    )


@router.callback_query(F.data.startswith("sale_variant_"))
async def sale_variant_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("sale_variant_", "")

    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()

    await state.update_data(
        variant_id=variant_id,
        variant_name=f"{variant.product.name} — {variant.name}",
        variant_price=float(variant.price),
        variant_qty=variant.quantity,
    )
    await state.set_state(SaleState.waiting_quantity)

    await callback.message.edit_text(
        f"✅ *{variant.product.name} — {variant.name}*\n"
        f"Narxi: *{variant.price:,} so'm*\n"
        f"Omborda: *{variant.quantity} dona*\n\n"
        f"Nechta sotildi?",
        reply_markup=quantity_keyboard()
    )


@router.callback_query(SaleState.waiting_quantity, F.data.startswith("qty_"))
async def sale_quantity_chosen(callback: CallbackQuery, state: FSMContext):
    if callback.data == "qty_custom":
        await callback.message.edit_text("Miqdorni kiriting (raqam):")
        return

    quantity = int(callback.data.replace("qty_", ""))
    await state.update_data(quantity=quantity)
    await state.set_state(SaleState.waiting_payment)

    data = await state.get_data()
    await callback.message.edit_text(
        f"📦 *{data['variant_name']}*\n"
        f"🔢 Miqdor: *{quantity} dona*\n"
        f"💰 Summa: *{data['variant_price'] * quantity:,.0f} so'm*\n\n"
        f"To'lov turini tanlang:",
        reply_markup=payment_keyboard()
    )


@router.message(SaleState.waiting_quantity)
async def sale_quantity_manual(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer("Raqam kiriting. Masalan: 7")
        return

    await state.update_data(quantity=quantity)
    await state.set_state(SaleState.waiting_payment)

    data = await state.get_data()
    await message.answer(
        f"📦 *{data['variant_name']}*\n"
        f"🔢 Miqdor: *{quantity} dona*\n"
        f"💰 Summa: *{data['variant_price'] * quantity:,.0f} so'm*\n\n"
        f"To'lov turini tanlang:",
        reply_markup=payment_keyboard()
    )


@router.callback_query(SaleState.waiting_payment, F.data.startswith("pay_"))
async def sale_payment_chosen(callback: CallbackQuery, state: FSMContext):
    payment_map = {
        'pay_cash': Sale.PaymentType.CASH,
        'pay_card': Sale.PaymentType.CARD,
        'pay_debt': Sale.PaymentType.DEBT,
    }

    payment_type = payment_map.get(callback.data)
    if not payment_type:
        await callback.message.edit_text("Noto'g'ri tanlov.")
        return

    # Qarzga sotilsa — mijoz tanlash
    if payment_type == Sale.PaymentType.DEBT:
        await state.update_data(payment_type='debt')
        await state.set_state(SaleState.waiting_customer)

        data = await state.get_data()
        store = await sync_to_async(Store.objects.get)(id=data['store_id'])

        customers = await sync_to_async(
            lambda: list(
                store.customers.filter(
                    is_deleted=False
                ).order_by('name').values('id', 'name')[:20]
            )
        )()

        if not customers:
            await callback.message.edit_text(
                "💳 *Qarzga sotuv*\n\n"
                "Hozircha mijoz yo'q.\n"
                "Yangi mijoz ismini kiriting:",
            )
            await state.set_state(SaleState.waiting_new_customer)
            return

        await callback.message.edit_text(
            "💳 *Qarzga sotuv*\n\nMijozni tanlang:",
            reply_markup=customers_keyboard(customers)
        )
        return

    # Naqd yoki karta — to'g'ridan yakunlash
    data = await state.get_data()
    await _complete_sale(
        event=callback,
        state=state,
        data=data,
        payment_type=payment_type,
        customer=None
    )


@router.callback_query(SaleState.waiting_customer, F.data.startswith("debt_customer_"))
async def debt_customer_chosen(callback: CallbackQuery, state: FSMContext):
    customer_id = callback.data.replace("debt_customer_", "")

    from apps.customers.models import Customer
    customer = await sync_to_async(Customer.objects.get)(id=customer_id)

    data = await state.get_data()
    await _complete_sale(
        event=callback,
        state=state,
        data=data,
        payment_type=Sale.PaymentType.DEBT,
        customer=customer
    )


@router.callback_query(SaleState.waiting_customer, F.data == "debt_new_customer")
async def debt_new_customer_btn(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SaleState.waiting_new_customer)
    await callback.message.edit_text("👤 Yangi mijoz ismini kiriting:")


@router.message(SaleState.waiting_new_customer)
async def debt_new_customer_name(message: Message, state: FSMContext):
    from apps.customers.models import Customer

    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])

    customer = await sync_to_async(Customer.objects.create)(
        store=store,
        name=message.text.strip(),
    )

    await _complete_sale(
        event=message,
        state=state,
        data=data,
        payment_type=Sale.PaymentType.DEBT,
        customer=customer
    )


async def _complete_sale(event, state, data, payment_type, customer=None):
    from django.core.exceptions import ValidationError
    import django.utils.timezone as tz

    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(
            id=data['variant_id']
        )
    )()

    store = await sync_to_async(Store.objects.get)(id=data['store_id'])

    try:
        sale = await sync_to_async(SaleService.create_sale)(
            store=store,
            items=[{'variant': variant, 'quantity': data['quantity']}],
            payment_type=payment_type,
            customer=customer,
        )

        variant_updated = await sync_to_async(
            lambda: ProductVariant.objects.get(id=data['variant_id'])
        )()

        customer_text = f"👤 Mijoz: *{customer.name}*\n" if customer else ""
        now = tz.localtime(sale.sold_at).strftime('%d.%m.%Y %H:%M')

        text = (
            f"✅ *Sotuv qayd etildi!*\n\n"
            f"📦 {data['variant_name']}\n"
            f"🔢 Miqdor: *{data['quantity']}* dona\n"
            f"💰 Summa: *{sale.total:,}* so'm\n"
            f"💳 To'lov: *{sale.get_payment_type_display()}*\n"
            f"{customer_text}"
            f"📊 Omborda qoldi: *{variant_updated.quantity}* dona\n"
            f"🕐 Vaqt: *{now}*"
        )

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
        else:
            await event.answer(text)

    except ValidationError as e:
        error_text = f"❌ Xato: {e.message}"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(error_text)
        else:
            await event.answer(error_text)

    await state.clear()


@router.callback_query(F.data == "sale_cancel")
async def sale_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")