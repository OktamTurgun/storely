import httpx
from django.conf import settings


async def transcribe_voice(file_path: str) -> str:
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                },
                data={"model": "whisper-1", "language": "uz"},
                files={"file": ("voice.ogg", f, "audio/ogg")},
                timeout=30,
            )

    response.raise_for_status()
    return response.json()['text']