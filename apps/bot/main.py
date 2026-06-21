import asyncio
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from django.conf import settings

from apps.bot.routers import start, sale, stock, debt, report, voice, image
from apps.bot.middlewares.auth import AuthMiddleware, RequireAuthMiddleware


async def main():
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    auth_router = Router()
    auth_router.message.middleware(RequireAuthMiddleware())
    auth_router.callback_query.middleware(RequireAuthMiddleware())
    auth_router.include_router(image.router)
    auth_router.include_router(voice.router)
    auth_router.include_router(sale.router)
    auth_router.include_router(stock.router)
    auth_router.include_router(debt.router)
    auth_router.include_router(report.router)

    dp.include_router(start.router)
    dp.include_router(auth_router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
