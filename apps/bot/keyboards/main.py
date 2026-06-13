from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Sotuv"),
                KeyboardButton(text="📥 Kirim"),
            ],
            [
                KeyboardButton(text="💳 Qarz"),
                KeyboardButton(text="✅ To'lash"),
            ],
            [
                KeyboardButton(text="📊 Bugungi hisobot"),
                KeyboardButton(text="⚠️ Kam qolganlar"),
            ],
        ],
        resize_keyboard=True,
    )