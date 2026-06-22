import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from apps.bot.services.parser import parse_command_ai


@pytest.mark.asyncio
async def test_parse_command_ai_sale():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"action": "sale", "product": "non", "quantity": 10, "payment_type": null, "customer": null}'
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await parse_command_ai("non 10 ta sotdim")
        assert result['action'] == 'sale'
        assert result['product'] == 'non'
        assert result['quantity'] == 10
        assert result['payment_type'] is None
        assert result['customer'] is None


@pytest.mark.asyncio
async def test_parse_command_ai_restock():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"action": "restock", "product": "un", "quantity": 5}'
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await parse_command_ai("5 qop un keldi")
        assert result['action'] == 'restock'
        assert result['product'] == 'un'
        assert result['quantity'] == 5


@pytest.mark.asyncio
async def test_parse_command_ai_debt():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"action": "debt", "customer": "Ali", "amount": 50000}'
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await parse_command_ai("Ali 50000 qarz")
        assert result['action'] == 'debt'
        assert result['customer'] == 'Ali'
        assert result['amount'] == 50000


@pytest.mark.asyncio
async def test_parse_command_ai_fallback_on_error():
    # If API fails, it should fallback to local parse_command regex
    with patch("httpx.AsyncClient", side_effect=Exception("API Error")):
        result = await parse_command_ai("non 10 dona sotdim")
        # should use regex fallback
        assert result['action'] == 'sale'
        assert result['product'] == 'non'
        assert result['quantity'] == 10
