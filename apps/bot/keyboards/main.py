from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


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
            [
                KeyboardButton(text="🗂 Mahsulotlar"),
                KeyboardButton(text="👥 Mijozlar"),
            ],
            [
                KeyboardButton(text="⚙️ Sozlamalar"),
            ],
        ],
        resize_keyboard=True,
    )


def products_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Ro'yxat", callback_data="prod_list"),
            InlineKeyboardButton(text="➕ Qo'shish", callback_data="prod_add"),
        ],
        [
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="prod_edit"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data="prod_delete"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])


def customers_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Ro'yxat", callback_data="cust_list"),
            InlineKeyboardButton(text="➕ Qo'shish", callback_data="cust_add"),
        ],
        [
            InlineKeyboardButton(text="🗑 O'chirish", callback_data="cust_delete"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])


def settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Do'kon nomini o'zgartirish", callback_data="set_store_name")],
        [InlineKeyboardButton(text="📊 Minimal chegara (ogohlantirish)", callback_data="set_threshold")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])