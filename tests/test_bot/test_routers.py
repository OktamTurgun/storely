import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext

from apps.bot.routers.voice import voice_handler, VoiceSaleState
from apps.bot.routers.image import image_variant_chosen, ImageSaleState
from apps.inventory.models import ProductVariant
from apps.customers.models import Customer
from apps.sales.models import Sale
from apps.debts.models import Debt


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestBotRouters:

    @pytest.fixture
    def fsm_state(self):
        state = AsyncMock(spec=FSMContext)
        state.storage = {}
        async def mock_update_data(**kwargs):
            state.storage.update(kwargs)
            return state.storage
        async def mock_get_data():
            return state.storage
        state.update_data.side_effect = mock_update_data
        state.get_data.side_effect = mock_get_data
        return state

    async def test_voice_sale_handler_one_variant(self, store, variant, user, fsm_state):
        message = AsyncMock()
        message.voice.file_id = "voice_file_1"
        message.answer = AsyncMock()

        bot = MagicMock()
        bot.get_file = AsyncMock()
        bot.download_file = AsyncMock()

        with patch("apps.bot.routers.voice.transcribe_voice", return_value="Pepsi 2 dona sotdim"), \
             patch("apps.bot.routers.voice.parse_command_ai", return_value={
                 "action": "sale", "product": "Pepsi", "quantity": 2, "payment_type": None, "customer": None
             }), \
             patch("os.unlink"):
            await voice_handler(message, bot, fsm_state, user)

        message.answer.assert_any_call("🗣 Tanildi: _Pepsi 2 dona sotdim_")
        fsm_state.update_data.assert_any_call(store_id=str(store.id), quantity=2)
        fsm_state.update_data.assert_any_call(variant_id=str(variant.id))
        fsm_state.set_state.assert_called_with(VoiceSaleState.waiting_payment)

    async def test_voice_restock_handler(self, store, variant, user, fsm_state):
        message = AsyncMock()
        message.voice.file_id = "voice_file_2"
        message.answer = AsyncMock()

        bot = MagicMock()
        bot.get_file = AsyncMock()
        bot.download_file = AsyncMock()

        from apps.bot.routers.voice import VoiceRestockState
        with patch("apps.bot.routers.voice.transcribe_voice", return_value="Pepsi 5 dona keldi"), \
             patch("apps.bot.routers.voice.parse_command_ai", return_value={
                 "action": "restock", "product": "Pepsi", "quantity": 5
             }), \
             patch("os.unlink"):
            await voice_handler(message, bot, fsm_state, user)

        fsm_state.update_data.assert_any_call(quantity=5)
        fsm_state.update_data.assert_any_call(variant_id=str(variant.id))
        fsm_state.set_state.assert_called_with(VoiceRestockState.waiting_confirm)

    async def test_voice_debt_handler_new_customer(self, store, user, fsm_state):
        message = AsyncMock()
        message.voice.file_id = "voice_file_3"
        message.answer = AsyncMock()

        bot = MagicMock()
        bot.get_file = AsyncMock()
        bot.download_file = AsyncMock()

        from apps.bot.routers.voice import VoiceDebtState
        with patch("apps.bot.routers.voice.transcribe_voice", return_value="Ali 30000 qarz"), \
             patch("apps.bot.routers.voice.parse_command_ai", return_value={
                 "action": "debt", "customer": "Ali", "amount": 30000
             }), \
             patch("os.unlink"):
            await voice_handler(message, bot, fsm_state, user)

        fsm_state.update_data.assert_called_with(
            store_id=str(store.id),
            customer_name="Ali",
            amount=30000,
        )
        fsm_state.set_state.assert_called_with(VoiceDebtState.waiting_customer)
