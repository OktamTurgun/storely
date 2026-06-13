from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from apps.debts.models import Debt
from apps.debts.services import DebtService
from apps.stores.models import Store

router = Router()


class PayDebtState(StatesGroup):
    waiting_customer = State()
    waiting_amount = State()


@router.message(F.text == "💳 Qarz")
async def debt_list(message: Message, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    debts = await sync_to_async(
        lambda: list(
            DebtService.get_store_debts(store)
            .select_related('customer')[:10]
        )
    )()

    if not debts:
        await message.answer("✅ Hozircha qarzdor yo'q!")
        return

    lines = ["💳 *Qarzdorlar ro'yxati:*\n"]
    for d in debts:
        lines.append(f"• {d.customer.name}: *{d.remaining:,} so'm*")

    await message.answer("\n".join(lines))


@router.message(F.text == "✅ To'lash")
async def pay_start(message: Message, state: FSMContext):
    await message.answer("Mijoz ismini kiriting:")
    await state.set_state(PayDebtState.waiting_customer)


@router.message(PayDebtState.waiting_customer)
async def pay_customer(message: Message, state: FSMContext, user):
    store = await sync_to_async(
        Store.objects.filter(owner=user, is_deleted=False).first
    )()

    debt = await sync_to_async(
        Debt.objects.filter(
            store=store,
            customer__name__icontains=message.text,
            is_closed=False,
            is_deleted=False,
        ).select_related('customer').first
    )()

    if not debt:
        await message.answer("Mijoz topilmadi. Qaytadan kiriting:")
        return

    await state.update_data(debt_id=str(debt.id))
    await state.set_state(PayDebtState.waiting_amount)
    await message.answer(
        f"*{debt.customer.name}* ning qarzi: "
        f"*{debt.remaining:,} so'm*\n\n"
        f"To'lov summasini kiriting:"
    )


@router.message(PayDebtState.waiting_amount)
async def pay_amount(message: Message, state: FSMContext, user):
    try:
        amount = int(message.text.replace(' ', '').replace(',', ''))
    except ValueError:
        await message.answer("Raqam kiriting. Masalan: 50000")
        return

    data = await state.get_data()
    debt = await sync_to_async(Debt.objects.get)(id=data['debt_id'])

    from django.core.exceptions import ValidationError
    try:
        await sync_to_async(DebtService.pay_debt)(debt, amount)
        debt = await sync_to_async(Debt.objects.get)(id=data['debt_id'])
        await message.answer(
            f"✅ *{amount:,} so'm* qabul qilindi.\n"
            f"Qoldiq: *{debt.remaining:,} so'm*"
        )
    except ValidationError as e:
        await message.answer(f"❌ Xato: {e.message}")

    await state.clear()