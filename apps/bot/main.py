import asyncio
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from django.conf import settings

from apps.bot.routers import start, sale, stock, debt, report, voice, image
from apps.bot.middlewares.auth import AuthMiddleware


async def main():
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())

    dp.include_router(start.router)
    dp.include_router(image.router)
    dp.include_router(voice.router)
    dp.include_router(sale.router)
    dp.include_router(stock.router)
    dp.include_router(debt.router)
    dp.include_router(report.router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())