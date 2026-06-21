from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.accounts.services import AccountService
from apps.bot.keyboards.main import main_menu

router = Router()


class OnboardingState(StatesGroup):
    waiting_store_name = State()
    waiting_phone = State()


@router.message(CommandStart())
async def start_handler(message: Message, user, state: FSMContext):
    if user:
        await state.clear()
        await message.answer(
            f"Salom, *{user.get_full_name() or user.username}*! 👋\n\n"
            f"Men sizning aqlli omborxona yordamchingizman.\n"
            f"Quyidagi tugmalardan foydalaning:",
            reply_markup=main_menu(),
        )
        return

    await state.set_state(OnboardingState.waiting_store_name)
    await message.answer(
        "Salom! 👋 *Storely* ga xush kelibsiz.\n\n"
        "Bu bot kichik do'konlar uchun ombor, sotuv va qarzlarni "
        "boshqarishga yordam beradi.\n\n"
        "Boshlash uchun *do'koningiz nomini* kiriting:"
    )


@router.message(OnboardingState.waiting_store_name)
async def onboarding_store_name(message: Message, state: FSMContext):
    store_name = (message.text or '').strip()
    if len(store_name) < 2:
        await message.answer("Iltimos, kamida 2 ta belgidan iborat do'kon nomini kiriting.")
        return

    await state.update_data(store_name=store_name)
    await state.set_state(OnboardingState.waiting_phone)
    await message.answer(
        f"✅ Do'kon: *{store_name}*\n\n"
        "Telefon raqamingizni kiriting (ixtiyoriy).\n"
        "O'tkazib yuborish uchun /skip yozing."
    )


@router.message(OnboardingState.waiting_phone, Command('skip'))
async def onboarding_skip_phone(message: Message, state: FSMContext):
    await _complete_onboarding(message, state, phone='')


@router.message(OnboardingState.waiting_phone)
async def onboarding_phone(message: Message, state: FSMContext):
    phone = (message.text or '').strip()
    await _complete_onboarding(message, state, phone=phone)


async def _complete_onboarding(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    store_name = data.get('store_name', '').strip()
    tg_user = message.from_user
    telegram_id = str(tg_user.id)
    telegram_name = tg_user.full_name or tg_user.first_name or ''

    try:
        user, store = await sync_to_async(AccountService.register_from_telegram)(
            telegram_id=telegram_id,
            telegram_name=telegram_name,
            store_name=store_name,
            phone=phone,
        )
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"🎉 *Tabriklaymiz!*\n\n"
        f"🏪 Do'kon: *{store.name}*\n"
        f"👤 Hisob: *{user.get_full_name() or user.username}*\n\n"
        f"Endi quyidagi tugmalar orqali ishlashingiz mumkin:",
        reply_markup=main_menu(),
    )


@router.message(Command('help'))
async def help_handler(message: Message, user):
    if not user:
        await message.answer(
            "📌 *Storely* — kichik do'konlar uchun Telegram bot.\n\n"
            "Ro'yxatdan o'tish uchun /start buyrug'ini yuboring."
        )
        return

    await message.answer(
        "📌 *Buyruqlar:*\n\n"
        "📦 *Sotuv* — mahsulot sotish\n"
        "📥 *Kirim* — omborga mahsulot qo'shish\n"
        "💳 *Qarz* — qarzdorlar ro'yxati\n"
        "✅ *To'lash* — qarz to'lash\n"
        "📊 *Bugungi hisobot* — kunlik statistika\n"
        "⚠️ *Kam qolganlar* — tugayotgan mahsulotlar\n\n"
        "🎤 Ovozli xabar ham yuborishingiz mumkin!\n"
        "📷 Rasm yuborib mahsulot tanishingiz mumkin!"
    )
