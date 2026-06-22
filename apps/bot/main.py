import asyncio
import django
import logging
import os
import sys

# Loyiha ildiz papkasini importlar uchun sys.path ga qo'shamiz
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from django.conf import settings

from apps.bot.routers import start, sale, stock, debt, report, voice, image, products, customers, settings as settings_router
from apps.bot.middlewares.auth import AuthMiddleware, RequireAuthMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
    auth_router.include_router(products.router)
    auth_router.include_router(customers.router)
    auth_router.include_router(settings_router.router)

    dp.include_router(start.router)
    dp.include_router(auth_router)

    logger.info("🤖 Bot ishga tushdi!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Foydalanuvchi tomonidan to'xtatildi (Ctrl+C).")
