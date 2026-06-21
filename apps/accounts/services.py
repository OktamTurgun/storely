from django.db import transaction
from django.contrib.auth import get_user_model
from apps.stores.models import Store

User = get_user_model()


class AccountService:

    @staticmethod
    @transaction.atomic
    def register_from_telegram(
        telegram_id: str,
        telegram_name: str,
        store_name: str,
        phone: str = '',
    ):
        if User.objects.filter(telegram_id=telegram_id).exists():
            raise ValueError('Bu Telegram hisob allaqachon ro\'yxatdan o\'tgan.')

        username = f'tg_{telegram_id}'
        user = User.objects.create_user(
            username=username,
            first_name=telegram_name[:150] or username,
            telegram_id=telegram_id,
        )
        store = Store.objects.create(
            owner=user,
            name=store_name,
            phone=phone,
        )
        return user, store
