from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable[Any]],
        event: Message,
        data: dict
    ) -> Any:
        telegram_id = str(event.from_user.id)

        user = await sync_to_async(
            User.objects.filter(telegram_id=telegram_id).first
        )()

        if not user:
            await event.answer(
                "Siz ro'yxatdan o'tmagansiz.\n"
                "Iltimos, web orqali ro'yxatdan o'ting va "
                "Telegram ID ni bog'lang."
            )
            return

        data['user'] = user
        return await handler(event, data)