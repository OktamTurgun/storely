import httpx
import base64
import json
from django.conf import settings


def encode_image(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


async def recognize_product(file_path: str, store_products: list[str]) -> dict | None:
    image_data = encode_image(file_path)
    products_list = "\n".join(f"- {p}" for p in store_products)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            },
            json={
                "model": "gpt-4o",
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Bu rasmda qaysi mahsulot ko'rinmoqda?\n\n"
                                    f"Do'kondagi mahsulotlar:\n{products_list}\n\n"
                                    f"Faqat JSON javob ber:\n"
                                    f'{{"product_name": "...", '
                                    f'"confidence": "high|low", '
                                    f'"description": "..."}}\n\n'
                                    f"Topilmasa — product_name: null"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ]
            },
            timeout=30,
        )

    response.raise_for_status()
    text = response.json()['choices'][0]['message']['content']

    try:
        clean = text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean)
    except Exception:
        return None