"""
Mijozlar boshqaruvi routeri.
Bot ichidan mijoz qo'shish, ko'rish, o'chirish.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.stores.models import Store
from apps.customers.models import Customer
from apps.debts.models import Debt

router = Router()


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class AddCustomerState(StatesGroup):
    waiting_name = State()
    waiting_phone = State()


class DeleteCustomerState(StatesGroup):
    choosing_customer = State()
    confirming = State()


# ---------------------------------------------------------------------------
# Entry point: "👥 Mijozlar" tugmasi
# ---------------------------------------------------------------------------

@router.message(F.text == "👥 Mijozlar")
async def customers_main(message: Message, state: FSMContext):
    await state.clear()
    from apps.bot.keyboards.main import customers_menu
    await message.answer(
        "👥 *Mijozlar boshqaruvi*\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=customers_menu(),
    )


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cust_list")
async def cust_list(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await callback.message.edit_text("Do'koningiz topilmadi.")
        return

    customers = await sync_to_async(
        lambda: list(
            Customer.objects.filter(store=store, is_deleted=False)
            .order_by('name')
        )
    )()

    if not customers:
        await callback.message.edit_text(
            "👥 Hali mijoz qo'shilmagan.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Mijoz qo'shish", callback_data="cust_add")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")],
            ])
        )
        return

    # Har bir mijozning qarzini olish
    lines = [f"👥 *Mijozlar ro'yxati* ({len(customers)} ta):\n"]
    for c in customers:
        from django.db.models import Sum
        debt_agg = await sync_to_async(
            lambda cust=c: Debt.objects.filter(
                customer=cust, is_closed=False, is_deleted=False
            ).aggregate(
                total_amount=Sum('amount'),
                total_paid=Sum('paid'),
            )
        )()
        total_amount = debt_agg.get('total_amount') or 0
        total_paid = debt_agg.get('total_paid') or 0
        total_remaining = total_amount - total_paid
        debt_text = f"💳 Qarzi: *{total_remaining:,} so'm*" if total_remaining > 0 else "✅ Qarzsiz"
        lines.append(f"👤 *{c.name}*\n   {debt_text}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Qo'shish", callback_data="cust_add")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")],
        ])
    )


# ---------------------------------------------------------------------------
# ADD CUSTOMER
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cust_add")
async def cust_add_start(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await callback.message.edit_text("Do'koningiz topilmadi.")
        return

    await state.update_data(store_id=str(store.id))
    await state.set_state(AddCustomerState.waiting_name)
    await callback.message.edit_text(
        "➕ *Yangi mijoz qo'shish*\n\n"
        "👤 Mijoz *ismini* kiriting:"
    )


@router.message(AddCustomerState.waiting_name)
async def cust_add_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Ism kamida 2 ta harf bo'lishi kerak.")
        return
    await state.update_data(customer_name=name)
    await state.set_state(AddCustomerState.waiting_phone)
    await message.answer(
        f"✅ Ism: *{name}*\n\n"
        "📱 Telefon raqamini kiriting (ixtiyoriy):\n"
        "_O'tkazish uchun /skip yozing_"
    )


@router.message(AddCustomerState.waiting_phone, Command('skip'))
async def cust_add_phone_skip(message: Message, state: FSMContext):
    await _save_customer(message, state, phone="")


@router.message(AddCustomerState.waiting_phone)
async def cust_add_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await _save_customer(message, state, phone=phone)


async def _save_customer(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    name = data['customer_name']

    # Duplicate tekshirish
    existing = await sync_to_async(
        lambda: Customer.objects.filter(
            store=store, name__iexact=name, is_deleted=False
        ).first()
    )()

    if existing:
        await message.answer(
            f"⚠️ *{name}* ismli mijoz allaqachon mavjud.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Ro'yxat", callback_data="cust_list")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")],
            ])
        )
        await state.clear()
        return

    customer = await sync_to_async(Customer.objects.create)(
        store=store,
        name=name,
        phone=phone,
    )

    await message.answer(
        f"🎉 *Mijoz qo'shildi!*\n\n"
        f"👤 Ism: *{customer.name}*\n"
        f"📱 Telefon: *{phone or '—'}*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yana qo'shish", callback_data="cust_add")],
            [InlineKeyboardButton(text="👥 Ro'yxat", callback_data="cust_list")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")],
        ])
    )
    await state.clear()


# ---------------------------------------------------------------------------
# DELETE CUSTOMER
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cust_delete")
async def cust_delete_start(callback: CallbackQuery, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await callback.message.edit_text("Do'koningiz topilmadi.")
        return

    customers = await sync_to_async(
        lambda: list(
            Customer.objects.filter(store=store, is_deleted=False).order_by('name')[:20]
        )
    )()

    if not customers:
        await callback.message.edit_text(
            "👥 O'chirish uchun mijoz yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")]
            ])
        )
        return

    buttons = []
    for c in customers:
        buttons.append([InlineKeyboardButton(
            text=f"👤 {c.name}",
            callback_data=f"cust_del_{c.id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cust_back")])

    await state.set_state(DeleteCustomerState.choosing_customer)
    await callback.message.edit_text(
        "🗑 *Qaysi mijozni o'chirmoqchisiz?*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(DeleteCustomerState.choosing_customer, F.data.startswith("cust_del_"))
async def cust_delete_chosen(callback: CallbackQuery, state: FSMContext):
    customer_id = callback.data.replace("cust_del_", "")
    customer = await sync_to_async(Customer.objects.get)(id=customer_id)

    # Qarz tekshirish
    has_debt = await sync_to_async(
        lambda: Debt.objects.filter(
            customer=customer, is_closed=False, is_deleted=False
        ).exists()
    )()

    await state.update_data(delete_customer_id=customer_id)
    await state.set_state(DeleteCustomerState.confirming)

    debt_warning = "\n\n⚠️ *Bu mijozning ochiq qarzlari bor!*" if has_debt else ""

    await callback.message.edit_text(
        f"🗑 *O'chirishni tasdiqlaysizmi?*\n\n"
        f"👤 *{customer.name}*{debt_warning}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data="cust_del_confirm_yes"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="cust_back"),
            ]
        ])
    )


@router.callback_query(DeleteCustomerState.confirming, F.data == "cust_del_confirm_yes")
async def cust_delete_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    customer = await sync_to_async(Customer.objects.get)(id=data['delete_customer_id'])
    name = customer.name

    customer.is_deleted = True
    await sync_to_async(customer.save)(update_fields=['is_deleted', 'updated_at'])

    await callback.message.edit_text(
        f"✅ *{name}* mijozi o'chirildi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Ro'yxat", callback_data="cust_list")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cust_back")],
        ])
    )
    await state.clear()


# ---------------------------------------------------------------------------
# Back handler
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cust_back")
async def cust_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from apps.bot.keyboards.main import customers_menu
    await callback.message.edit_text(
        "👥 *Mijozlar boshqaruvi*\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=customers_menu(),
    )
