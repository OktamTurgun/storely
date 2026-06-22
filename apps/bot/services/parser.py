import re
import httpx
import json
from django.conf import settings


def parse_command(text: str) -> dict | None:
    text = text.lower().strip()

    if any(w in text for w in ['statistika', 'hisobot', 'daromad']):
        return {'action': 'report'}

    sale_match = re.search(
        r'(\w+)\s+(\d+)\s*(?:dona|ta|kg|litr)?\s*'
        r'(?:sotdim|sotildi|ketdi)',
        text
    )
    if sale_match:
        return {
            'action': 'sale',
            'product': sale_match.group(1),
            'quantity': int(sale_match.group(2)),
        }

    restock_match = re.search(
        r'(\d+)\s*(?:dona|ta|kg|qop|litr)?\s*(\w+)\s*'
        r'(?:keldi|qo\'shildi|kirim)',
        text
    )
    if restock_match:
        return {
            'action': 'restock',
            'quantity': int(restock_match.group(1)),
            'product': restock_match.group(2),
        }

    debt_match = re.search(
        r'(\w+)\s+(\d[\d\s]*)\s*(?:so\'m)?\s*(?:qarzga|qarz)',
        text
    )
    if debt_match:
        amount_str = debt_match.group(2).replace(' ', '')
        return {
            'action': 'debt',
            'customer': debt_match.group(1),
            'amount': int(amount_str),
        }

    return None


async def parse_command_ai(text: str) -> dict | None:
    """Uses OpenAI API to parse conversational Uzbek shop commands into structured JSON."""
    system_prompt = (
        "You are an Uzbek language natural language parser for an inventory and shop management bot.\n"
        "Your job is to parse conversational Uzbek shop commands into structured JSON.\n"
        "Recognize the following actions:\n"
        "1. \"sale\" - Selling a product.\n"
        "   Requires: \"product\" (string, product name), \"quantity\" (integer, amount sold), and optionally \"payment_type\" (\"cash\" | \"card\" | \"debt\"), and \"customer\" (string | null).\n"
        "   Examples:\n"
        "   - \"non 10 dona sotdim\" -> {\"action\": \"sale\", \"product\": \"non\", \"quantity\": 10, \"payment_type\": null, \"customer\": null}\n"
        "   - \"besh dona cola ketdi\" -> {\"action\": \"sale\", \"product\": \"cola\", \"quantity\": 5, \"payment_type\": null, \"customer\": null}\n"
        "   - \"ali 10 ta non qarzga oldi\" -> {\"action\": \"sale\", \"product\": \"non\", \"quantity\": 10, \"payment_type\": \"debt\", \"customer\": \"ali\"}\n"
        "2. \"restock\" - Restocking/incoming inventory.\n"
        "   Requires: \"product\" (string, product name), \"quantity\" (integer, amount added).\n"
        "   Examples:\n"
        "   - \"5 qop un keldi\" -> {\"action\": \"restock\", \"product\": \"un\", \"quantity\": 5}\n"
        "   - \"10 ta fanta qo'shildi\" -> {\"action\": \"restock\", \"product\": \"fanta\", \"quantity\": 10}\n"
        "3. \"debt\" - Creating a debt for a customer directly without sale items.\n"
        "   Requires: \"customer\" (string, customer name), \"amount\" (integer, debt amount in soums).\n"
        "   Examples:\n"
        "   - \"Sardorga 50000 qarz\" -> {\"action\": \"debt\", \"customer\": \"Sardor\", \"amount\": 50000}\n"
        "   - \"ali 25000 qarzga\" -> {\"action\": \"debt\", \"customer\": \"ali\", \"amount\": 25000}\n"
        "4. \"report\" - Showing daily statistics/report.\n"
        "   Requires: no extra fields.\n"
        "   Examples: \"bugungi statistika\", \"hisobot ko'rsat\", \"bugun qancha sotdik\" -> {\"action\": \"report\"}\n\n"
        "Respond ONLY with a JSON object in this format (no markdown code blocks, no extra text):\n"
        "{\n"
        "  \"action\": \"sale\" | \"restock\" | \"debt\" | \"report\" | null,\n"
        "  \"product\": string | null,\n"
        "  \"quantity\": integer | null,\n"
        "  \"customer\": string | null,\n"
        "  \"amount\": integer | null,\n"
        "  \"payment_type\": \"cash\" | \"card\" | \"debt\" | null\n"
        "}\n"
        "If you cannot understand the command or it does not match any of these actions, set \"action\" to null."
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                },
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 150,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0,
                },
                timeout=15,
            )
        response.raise_for_status()
        res_data = response.json()
        content = res_data['choices'][0]['message']['content'].strip()
        
        # Clean any potential markdown blocks
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
            
        parsed = json.loads(content)
        if parsed.get('action') is None:
            return None
        return parsed
    except Exception:
        # Fallback to local regex if API fails
        return parse_command(text)