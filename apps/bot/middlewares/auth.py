from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthMiddleware(BaseMiddleware):
    """Telegram ID bo'yicha foydalanuvchini topadi va data['user'] ga qo'yadi."""

    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable[Any]],
        event,
        data: dict,
    ) -> Any:
        if isinstance(event, CallbackQuery):
            tg_user = event.from_user
        else:
            tg_user = event.from_user

        telegram_id = str(tg_user.id)

        user = await sync_to_async(
            User.objects.filter(telegram_id=telegram_id).first
        )()

        data['user'] = user
        return await handler(event, data)


class RequireAuthMiddleware(BaseMiddleware):
    """Ro'yxatdan o'tmagan foydalanuvchilarni bloklaydi."""

    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable[Any]],
        event,
        data: dict,
    ) -> Any:
        user = data.get('user')
        if not user:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "Avval ro'yxatdan o'ting: /start",
                    show_alert=True,
                )
            else:
                await event.answer(
                    "Siz hali ro'yxatdan o'tmagansiz.\n"
                    "Boshlash uchun /start buyrug'ini yuboring."
                )
            return

        return await handler(event, data)
