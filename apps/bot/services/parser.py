import re


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