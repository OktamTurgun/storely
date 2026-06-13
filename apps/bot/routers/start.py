from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from apps.bot.keyboards.main import main_menu

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, user):
    await message.answer(
        f"Salom, *{user.get_full_name()}*! 👋\n\n"
        f"Men sizning aqlli omborxona yordamchingizman.\n"
        f"Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu()
    )


@router.message(Command('help'))
async def help_handler(message: Message, user):
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