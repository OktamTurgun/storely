import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id: str, text: str, parse_mode: str = 'Markdown') -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN not set; skipping message to %s', chat_id)
        return False

    if not chat_id:
        logger.warning('Empty chat_id; skipping Telegram message')
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response = httpx.post(
            url,
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.error('Failed to send Telegram message to %s: %s', chat_id, exc)
        return False
