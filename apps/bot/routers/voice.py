import os
import tempfile
from aiogram import Router, F, Bot
from aiogram.types import Message
from apps.bot.services.whisper import transcribe_voice
from apps.bot.services.parser import parse_command

router = Router()


@router.message(F.voice)
async def voice_handler(message: Message, bot: Bot, user):
    await message.answer("🎤 Ovoz qabul qilindi, tahlil qilinmoqda...")

    voice = await bot.get_file(message.voice.file_id)

    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await bot.download_file(voice.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        text = await transcribe_voice(tmp_path)
        await message.answer(f"🗣 Tanildi: _{text}_")

        command = parse_command(text)

        if not command:
            await message.answer(
                "Buyruqni tushunmadim. Masalan:\n"
                "• 'Non 10 dona sotdim'\n"
                "• '5 qop un keldi'\n"
                "• 'Bugungi statistika'"
            )
            return

        if command['action'] == 'report':
            from apps.bot.routers.report import today_report
            await today_report(message, user)

        elif command['action'] == 'sale':
            await message.answer(
                f"✅ Sotuv qayd etildi:\n"
                f"• Mahsulot: *{command['product']}*\n"
                f"• Miqdor: *{command['quantity']}* dona"
            )

        elif command['action'] == 'restock':
            await message.answer(
                f"✅ Kirim qayd etildi:\n"
                f"• Mahsulot: *{command['product']}*\n"
                f"• Miqdor: *{command['quantity']}*"
            )

        elif command['action'] == 'debt':
            await message.answer(
                f"✅ Qarz qayd etildi:\n"
                f"• Mijoz: *{command['customer']}*\n"
                f"• Summa: *{command['amount']:,} so'm*"
            )
    finally:
        os.unlink(tmp_path)