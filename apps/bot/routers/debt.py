"""
Qarz boshqaruvi routeri — to'liq qayta yozilgan.
- Qarzdorlar ro'yxati (paginatsiya bilan)
- Har bir mijozning barcha qarzlari
- Inline tugmalar orqali to'lash
- To'liq to'langan qarzlar arxivi
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.debts.models import Debt
from apps.debts.services import DebtService
from apps.stores.models import Store

router = Router()


class PayDebtState(StatesGroup):
    waiting_amount = State()


# ---------------------------------------------------------------------------
# 💳 Qarzdorlar ro'yxati
# ---------------------------------------------------------------------------

@router.message(F.text == "💳 Qarz")
async def debt_list(message: Message, state: FSMContext, user):
    await state.clear()
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    await _show_debt_list(message, store, edit=False)


async def _show_debt_list(event, store, edit=False):
    """Ochiq qarzlar ro'yxatini ko'rsatadi."""
    from django.db.models import Sum

    # Mijozlar bo'yicha guruhlab yig'ish
    debts_qs = await sync_to_async(
        lambda: list(
            Debt.objects.filter(
                store=store,
                is_closed=False,
                is_deleted=False,
            )
            .select_related('customer')
            .order_by('customer__name', '-created_at')
        )
    )()

    if not debts_qs:
        text = "✅ *Hozircha ochiq qarz yo'q!*\n\nBarcha qarzlar to'langan."
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 To'langan qarzlar", callback_data="debt_closed_list")],
        ])
        if edit:
            await event.message.edit_text(text, reply_markup=markup)
        else:
            await event.answer(text, reply_markup=markup)
        return

    # Mijoz bo'yicha guruhlash
    customers = {}
    for d in debts_qs:
        cid = d.customer.id
        if cid not in customers:
            customers[cid] = {'name': d.customer.name, 'total': 0, 'count': 0}
        customers[cid]['total'] += d.remaining
        customers[cid]['count'] += 1

    total_all = sum(c['total'] for c in customers.values())

    lines = [f"💳 *Qarzdorlar ro'yxati*\n💰 Jami: *{total_all:,} so'm*\n"]
    buttons = []
    for cid, info in customers.items():
        count_text = f"({info['count']} qarz)" if info['count'] > 1 else ""
        lines.append(f"👤 *{info['name']}* — {info['total']:,} so'm {count_text}")
        buttons.append([InlineKeyboardButton(
            text=f"👤 {info['name']} — {info['total']:,} so'm",
            callback_data=f"debt_cust_{cid}"
        )])

    buttons.append([InlineKeyboardButton(text="📋 To'langan qarzlar", callback_data="debt_closed_list")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    if edit:
        await event.message.edit_text("\n".join(lines), reply_markup=markup)
    else:
        await event.answer("\n".join(lines), reply_markup=markup)


# ---------------------------------------------------------------------------
# Mijozning barcha qarzlari
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("debt_cust_"))
async def debt_customer_detail(callback: CallbackQuery, state: FSMContext, user):
    customer_id = callback.data.replace("debt_cust_", "")
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    debts = await sync_to_async(
        lambda: list(
            Debt.objects.filter(
                store=store,
                customer_id=customer_id,
                is_closed=False,
                is_deleted=False,
            ).select_related('customer').order_by('created_at')
        )
    )()

    if not debts:
        await callback.message.edit_text(
            "✅ Bu mijozning barcha qarzlari to'langan.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="debt_back_list")]
            ])
        )
        return

    customer = debts[0].customer
    total = sum(d.remaining for d in debts)

    lines = [
        f"👤 *{customer.name}*\n"
        f"💰 Jami qarz: *{total:,} so'm*\n"
    ]

    buttons = []
    for d in debts:
        import django.utils.timezone as tz
        date = tz.localtime(d.created_at).strftime('%d.%m.%Y')
        lines.append(
            f"📌 *{d.remaining:,} so'm* (jami: {d.amount:,})\n"
            f"   To'langan: {d.paid:,} | Sana: {date}"
        )
        buttons.append([InlineKeyboardButton(
            text=f"💵 To'lash: {d.remaining:,} so'm ({date})",
            callback_data=f"debt_pay_{d.id}"
        )])

    # Barchani birdan to'lash tugmasi
    if len(debts) > 1:
        buttons.insert(0, [InlineKeyboardButton(
            text=f"✅ Barchasini to'lash ({total:,} so'm)",
            callback_data=f"debt_pay_all_{customer_id}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="debt_back_list")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ---------------------------------------------------------------------------
# Qarz to'lash — aniq summa kiritish
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("debt_pay_") & ~F.data.startswith("debt_pay_all_"))
async def debt_pay_start(callback: CallbackQuery, state: FSMContext, user):
    debt_id = callback.data.replace("debt_pay_", "")
    debt = await sync_to_async(
        lambda: Debt.objects.select_related('customer').get(id=debt_id)
    )()

    # Xavfsizlik: faqat o'z do'konining qarzi
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if str(debt.store_id) != str(store.id):
        await callback.answer("❌ Ruxsat yo'q.", show_alert=True)
        return

    await state.update_data(debt_id=debt_id, pay_mode="single")
    await state.set_state(PayDebtState.waiting_amount)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ To'liq to'lash ({debt.remaining:,})", callback_data=f"debt_pay_full_{debt_id}"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"debt_cust_{debt.customer_id}")],
    ])

    await callback.message.edit_text(
        f"💳 *Qarz to'lash*\n\n"
        f"👤 Mijoz: *{debt.customer.name}*\n"
        f"💰 Qarz: *{debt.amount:,} so'm*\n"
        f"✅ To'langan: *{debt.paid:,} so'm*\n"
        f"📌 Qoldiq: *{debt.remaining:,} so'm*\n\n"
        f"To'lov summasini kiriting yoki to'liq to'lash tugmasini bosing:",
        reply_markup=markup
    )


@router.callback_query(F.data.startswith("debt_pay_full_"))
async def debt_pay_full(callback: CallbackQuery, state: FSMContext, user):
    debt_id = callback.data.replace("debt_pay_full_", "")
    await _process_payment(callback, state, user, debt_id, amount=None, pay_full=True)


@router.callback_query(F.data.startswith("debt_pay_all_"))
async def debt_pay_all(callback: CallbackQuery, state: FSMContext, user):
    """Mijozning barcha qarzlarini to'lash."""
    customer_id = callback.data.replace("debt_pay_all_", "")
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    debts = await sync_to_async(
        lambda: list(
            Debt.objects.filter(
                store=store,
                customer_id=customer_id,
                is_closed=False,
                is_deleted=False,
            ).select_related('customer')
        )
    )()

    if not debts:
        await callback.answer("Qarz topilmadi.", show_alert=True)
        return

    customer_name = debts[0].customer.name
    total = sum(d.remaining for d in debts)
    paid_count = 0

    from django.core.exceptions import ValidationError
    for d in debts:
        try:
            await sync_to_async(DebtService.pay_debt)(d, d.remaining)
            paid_count += 1
        except ValidationError:
            pass

    await callback.message.edit_text(
        f"✅ *{customer_name}* ning barcha qarzlari to'landi!\n\n"
        f"💰 To'langan: *{total:,} so'm* ({paid_count} ta qarz)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="debt_back_list")]
        ])
    )
    await state.clear()


@router.message(PayDebtState.waiting_amount)
async def debt_pay_amount(message: Message, state: FSMContext, user):
    try:
        amount = int(message.text.replace(' ', '').replace(',', ''))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ To'g'ri summa kiriting. Masalan: 50000")
        return

    data = await state.get_data()
    await _process_payment(message, state, user, data['debt_id'], amount=amount)


async def _process_payment(event, state, user, debt_id, amount=None, pay_full=False):
    from django.core.exceptions import ValidationError

    debt = await sync_to_async(
        lambda: Debt.objects.select_related('customer').get(id=debt_id)
    )()

    # Xavfsizlik: faqat o'z do'konining qarzi
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if str(debt.store_id) != str(store.id):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Ruxsat yo'q.", show_alert=True)
        return

    if pay_full:
        amount = int(debt.remaining)

    try:
        await sync_to_async(DebtService.pay_debt)(debt, amount)
        debt = await sync_to_async(
            lambda: Debt.objects.select_related('customer').get(id=debt_id)
        )()

        if debt.is_closed:
            status_text = f"🎉 *Qarz to'liq yopildi!*"
        else:
            status_text = f"✅ *To'lov qabul qilindi!*\n📌 Qoldiq: *{debt.remaining:,} so'm*"

        text = (
            f"{status_text}\n\n"
            f"👤 Mijoz: *{debt.customer.name}*\n"
            f"💵 To'langan: *{amount:,} so'm*"
        )

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="debt_back_list")]
        ])

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=markup)
        else:
            await event.answer(text, reply_markup=markup)

    except ValidationError as e:
        err = f"❌ Xato: {e.message}"
        if isinstance(event, CallbackQuery):
            await event.answer(err, show_alert=True)
        else:
            await event.answer(err)

    await state.clear()


# ---------------------------------------------------------------------------
# To'langan qarzlar arxivi
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "debt_closed_list")
async def debt_closed_list(callback: CallbackQuery, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    closed = await sync_to_async(
        lambda: list(
            Debt.objects.filter(
                store=store,
                is_closed=True,
                is_deleted=False,
            ).select_related('customer').order_by('-updated_at')[:20]
        )
    )()

    if not closed:
        await callback.message.edit_text(
            "📋 To'langan qarzlar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="debt_back_list")]
            ])
        )
        return

    import django.utils.timezone as tz
    lines = [f"📋 *To'langan qarzlar* (so'nggi {len(closed)} ta):\n"]
    for d in closed:
        date = tz.localtime(d.updated_at).strftime('%d.%m.%Y')
        lines.append(f"✅ *{d.customer.name}* — {d.amount:,} so'm ({date})")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="debt_back_list")]
        ])
    )


# ---------------------------------------------------------------------------
# ✅ To'lash (menyu tugmasi)
# ---------------------------------------------------------------------------

@router.message(F.text == "✅ To'lash")
async def pay_start(message: Message, state: FSMContext, user):
    await state.clear()
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    if not store:
        await message.answer("Do'koningiz topilmadi.")
        return

    await _show_debt_list(message, store, edit=False)


# ---------------------------------------------------------------------------
# Back handler
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "debt_back_list")
async def debt_back_list(callback: CallbackQuery, state: FSMContext, user):
    await state.clear()
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()
    await _show_debt_list(callback, store, edit=True)