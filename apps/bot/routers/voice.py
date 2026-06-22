import os
import tempfile
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from django.core.exceptions import ValidationError
from django.conf import settings

from apps.bot.services.whisper import transcribe_voice
from apps.bot.services.parser import parse_command_ai
from apps.stores.models import Store
from apps.inventory.models import ProductVariant
from apps.customers.models import Customer
from apps.sales.models import Sale

logger = logging.getLogger(__name__)

router = Router()


class VoiceSaleState(StatesGroup):
    waiting_variant = State()
    waiting_payment = State()
    waiting_new_customer = State()


class VoiceRestockState(StatesGroup):
    waiting_variant = State()
    waiting_confirm = State()


class VoiceDebtState(StatesGroup):
    waiting_customer = State()
    waiting_confirm = State()


def voice_payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Naqd", callback_data="vpay_cash"),
            InlineKeyboardButton(text="💳 Karta", callback_data="vpay_card"),
            InlineKeyboardButton(text="📋 Qarzga", callback_data="vpay_debt"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")]
    ])


@router.message(F.voice)
async def voice_handler(message: Message, bot: Bot, state: FSMContext, user):
    await state.clear()
    await message.answer("🎤 Ovoz qabul qilindi, tahlil qilinmoqda...")

    voice = await bot.get_file(message.voice.file_id)

    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await bot.download_file(voice.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        try:
            text = await transcribe_voice(tmp_path)
            await message.answer(f"🗣 Tanildi: _{text}_")
        except Exception as e:
            logger.error(f"Voice transcription error: {e}", exc_info=True)
            await message.answer(
                "❌ Ovozni aniqlash xizmatida xatolik yuz berdi (Masalan: OpenAI limiti tugagan yoki tarmoq xatosi). "
                "Iltimos, keyinroq urinib ko'ring yoki yozma ravishda kiriting."
            )
            return

        try:
            command = await parse_command_ai(text)
        except Exception as e:
            logger.error(f"Voice command parsing error: {e}", exc_info=True)
            await message.answer(
                "❌ Buyruqni tahlil qilishda xatolik yuz berdi (Masalan: OpenAI limiti yoki tarmoq xatosi). "
                "Iltimos, keyinroq urinib ko'ring yoki yozma ravishda kiriting."
            )
            return

        if not command:
            await message.answer(
                "Buyruqni tushunmadim. Masalan:\n"
                "• 'Non 10 dona sotdim'\n"
                "• '5 qop un keldi'\n"
                "• 'Bugungi statistika'\n"
                "• 'Sardorga 50000 qarz'"
            )
            return

        store = await sync_to_async(
            Store.objects.filter(owner=user, is_deleted=False).first
        )()

        if not store:
            await message.answer("Do'koningiz topilmadi. Avval /start orqali ro'yxatdan o'ting.")
            return

        action = command.get('action')

        if action == 'report':
            from apps.bot.routers.report import today_report
            await today_report(message, user)

        elif action == 'sale':
            product_query = (command.get('product') or '').strip()
            quantity = command.get('quantity') or 1
            payment_type = command.get('payment_type')
            customer_name = (command.get('customer') or '').strip()

            variants = await sync_to_async(
                lambda: list(
                    ProductVariant.objects.filter(
                        product__store=store,
                        product__name__icontains=product_query,
                        is_deleted=False,
                    ).select_related('product')
                )
            )()

            if not variants:
                await message.answer(f"❌ Omborda '{product_query}' nomli mahsulot topilmadi.")
                return

            await state.update_data(store_id=str(store.id), quantity=quantity)

            # Agar qarzga sotuv bo'lsa va mijoz nomi aytilgan bo'lsa, to'g'ri bog'lash
            if payment_type == 'debt' and customer_name:
                customers = await sync_to_async(
                    lambda: list(
                        store.customers.filter(
                            name__icontains=customer_name,
                            is_deleted=False
                        )
                    )
                )()
                if len(customers) == 1 and len(variants) == 1:
                    customer = customers[0]
                    variant = variants[0]
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"vpay_debt_confirm_{customer.id}"),
                            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
                        ]
                    ])
                    await message.answer(
                        f"💳 *Qarzga sotuvni tasdiqlaysizmi?*\n\n"
                        f"📦 {variant.product.name} — {variant.name}\n"
                        f"🔢 Miqdor: *{quantity}* dona\n"
                        f"💰 Summa: *{variant.price * quantity:,}* so'm\n"
                        f"👤 Mijoz: *{customer.name}*",
                        reply_markup=markup
                    )
                    await state.update_data(variant_id=str(variant.id))
                    await state.set_state(VoiceSaleState.waiting_payment)
                    return

            if len(variants) == 1:
                variant = variants[0]
                await state.update_data(variant_id=str(variant.id))
                await message.answer(
                    f"📦 *{variant.product.name} — {variant.name}*\n"
                    f"🔢 Miqdor: *{quantity}* dona\n"
                    f"💰 Summa: *{variant.price * quantity:,}* so'm\n\n"
                    f"To'lov turini tanlang:",
                    reply_markup=voice_payment_keyboard()
                )
                await state.set_state(VoiceSaleState.waiting_payment)
            else:
                buttons = []
                for v in variants:
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"{v.product.name} — {v.name} | {v.price:,} so'm",
                            callback_data=f"vs_variant_{v.id}"
                        )
                    ])
                buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer(
                    f"🔍 Bir nechta mos mahsulot topildi. Tanlang (miqdori: {quantity} dona):",
                    reply_markup=markup
                )
                await state.set_state(VoiceSaleState.waiting_variant)

        elif action == 'restock':
            product_query = (command.get('product') or '').strip()
            quantity = command.get('quantity') or 1

            variants = await sync_to_async(
                lambda: list(
                    ProductVariant.objects.filter(
                        product__store=store,
                        product__name__icontains=product_query,
                        is_deleted=False,
                    ).select_related('product')
                )
            )()

            if not variants:
                await message.answer(f"❌ Omborda '{product_query}' nomli mahsulot topilmadi.")
                return

            await state.update_data(quantity=quantity)

            if len(variants) == 1:
                variant = variants[0]
                await state.update_data(variant_id=str(variant.id))
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="vr_confirm"),
                        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
                    ]
                ])
                await message.answer(
                    f"📥 *Kirimni tasdiqlaysizmi?*\n\n"
                    f"📦 Mahsulot: *{variant.product.name} — {variant.name}*\n"
                    f"➕ Miqdor: *{quantity}* dona\n"
                    f"📊 Ombordagi qoldiq: *{variant.quantity}* dona",
                    reply_markup=markup
                )
                await state.set_state(VoiceRestockState.waiting_confirm)
            else:
                buttons = []
                for v in variants:
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"{v.product.name} — {v.name} | {v.quantity} dona",
                            callback_data=f"vr_variant_{v.id}"
                        )
                    ])
                buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer(
                    f"🔍 Bir nechta mos mahsulot topildi. Kirim qilmoqchi bo'lganingizni tanlang (miqdori: {quantity} dona):",
                    reply_markup=markup
                )
                await state.set_state(VoiceRestockState.waiting_variant)

        elif action == 'debt':
            customer_query = (command.get('customer') or '').strip()
            amount = command.get('amount') or 0

            customers = await sync_to_async(
                lambda: list(
                    store.customers.filter(
                        name__icontains=customer_query,
                        is_deleted=False
                    )
                )
            )()

            await state.update_data(
                store_id=str(store.id),
                customer_name=customer_query,
                amount=amount,
            )

            if not customers:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Yangi mijoz yaratish va qarz yozish",
                            callback_data="vd_create_customer"
                        )
                    ],
                    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")]
                ])
                await message.answer(
                    f"👤 Mijoz *{customer_query}* topilmadi.\n"
                    f"Yangi mijoz yaratib, *{amount:,}* so'm qarz yozamizmi?",
                    reply_markup=markup
                )
                await state.set_state(VoiceDebtState.waiting_customer)
            elif len(customers) == 1:
                customer = customers[0]
                await state.update_data(customer_id=str(customer.id))
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="vd_confirm"),
                        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
                    ]
                ])
                await message.answer(
                    f"👤 *Qarzni tasdiqlaysizmi?*\n\n"
                    f"👤 Mijoz: *{customer.name}*\n"
                    f"💰 Summa: *{amount:,}* so'm",
                    reply_markup=markup
                )
                await state.set_state(VoiceDebtState.waiting_confirm)
            else:
                buttons = []
                for c in customers:
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"👤 {c.name}",
                            callback_data=f"vd_select_customer_{c.id}"
                        )
                    ])
                buttons.append([
                    InlineKeyboardButton(
                        text="➕ Yangi mijoz yaratish",
                        callback_data="vd_create_customer"
                    )
                ])
                buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer(
                    f"🔍 Bir nechta mos mijoz topildi. Tanlang (qarz: {amount:,} so'm):",
                    reply_markup=markup
                )
                await state.set_state(VoiceDebtState.waiting_customer)

    finally:
        os.unlink(tmp_path)


# Callback Handlers
@router.callback_query(F.data == "voice_cancel")
async def voice_cancel_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")


@router.callback_query(VoiceSaleState.waiting_variant, F.data.startswith("vs_variant_"))
async def voice_sale_variant_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("vs_variant_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    data = await state.get_data()
    quantity = data['quantity']
    await state.update_data(variant_id=variant_id)
    await state.set_state(VoiceSaleState.waiting_payment)
    await callback.message.edit_text(
        f"📦 *{variant.product.name} — {variant.name}*\n"
        f"🔢 Miqdor: *{quantity}* dona\n"
        f"💰 Summa: *{variant.price * quantity:,}* so'm\n\n"
        f"To'lov turini tanlang:",
        reply_markup=voice_payment_keyboard()
    )


@router.callback_query(VoiceSaleState.waiting_payment, F.data.startswith("vpay_"))
async def voice_sale_payment_chosen(callback: CallbackQuery, state: FSMContext):
    payment_map = {
        'vpay_cash': Sale.PaymentType.CASH,
        'vpay_card': Sale.PaymentType.CARD,
        'vpay_debt': Sale.PaymentType.DEBT,
    }
    payment_type = payment_map.get(callback.data)
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['variant_id'])
    )()
    quantity = data['quantity']

    if payment_type == Sale.PaymentType.DEBT:
        customers = await sync_to_async(
            lambda: list(
                store.customers.filter(is_deleted=False).order_by('name')[:20]
            )
        )()
        buttons = []
        for c in customers:
            buttons.append([
                InlineKeyboardButton(
                    text=f"👤 {c.name}",
                    callback_data=f"vpay_debt_cust_{c.id}"
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="➕ Yangi mijoz", callback_data="vpay_debt_new_cust")
        ])
        buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "💳 *Qarzga sotuv*\n\nMijozni tanlang:",
            reply_markup=markup
        )
        return

    await _complete_voice_sale(callback, state, store, variant, quantity, payment_type)


@router.callback_query(VoiceSaleState.waiting_payment, F.data.startswith("vpay_debt_cust_"))
async def voice_sale_debt_customer_chosen(callback: CallbackQuery, state: FSMContext):
    customer_id = callback.data.replace("vpay_debt_cust_", "")
    customer = await sync_to_async(Customer.objects.get)(id=customer_id)
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['variant_id'])
    )()
    quantity = data['quantity']
    await _complete_voice_sale(callback, state, store, variant, quantity, Sale.PaymentType.DEBT, customer)


@router.callback_query(VoiceSaleState.waiting_payment, F.data.startswith("vpay_debt_confirm_"))
async def voice_sale_debt_confirm_callback(callback: CallbackQuery, state: FSMContext):
    customer_id = callback.data.replace("vpay_debt_confirm_", "")
    customer = await sync_to_async(Customer.objects.get)(id=customer_id)
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['variant_id'])
    )()
    quantity = data['quantity']
    await _complete_voice_sale(callback, state, store, variant, quantity, Sale.PaymentType.DEBT, customer)


@router.callback_query(VoiceSaleState.waiting_payment, F.data == "vpay_debt_new_cust")
async def voice_sale_debt_new_customer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("👤 Yangi mijoz ismini kiriting:")
    await state.set_state(VoiceSaleState.waiting_new_customer)


@router.message(VoiceSaleState.waiting_new_customer)
async def voice_sale_new_customer_name(message: Message, state: FSMContext):
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['variant_id'])
    )()
    quantity = data['quantity']
    customer = await sync_to_async(Customer.objects.create)(
        store=store,
        name=message.text.strip(),
    )
    await _complete_voice_sale(message, state, store, variant, quantity, Sale.PaymentType.DEBT, customer)


# Restock callback handlers
@router.callback_query(VoiceRestockState.waiting_variant, F.data.startswith("vr_variant_"))
async def voice_restock_variant_chosen(callback: CallbackQuery, state: FSMContext):
    variant_id = callback.data.replace("vr_variant_", "")
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=variant_id)
    )()
    data = await state.get_data()
    quantity = data['quantity']
    await state.update_data(variant_id=variant_id)
    await state.set_state(VoiceRestockState.waiting_confirm)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="vr_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
        ]
    ])
    await callback.message.edit_text(
        f"📥 *Kirimni tasdiqlaysizmi?*\n\n"
        f"📦 Mahsulot: *{variant.product.name} — {variant.name}*\n"
        f"➕ Miqdor: *{quantity}* dona\n"
        f"📊 Ombordagi qoldiq: *{variant.quantity}* dona",
        reply_markup=markup
    )


@router.callback_query(VoiceRestockState.waiting_confirm, F.data == "vr_confirm")
async def voice_restock_confirmed(callback: CallbackQuery, state: FSMContext):
    from apps.inventory.services import ProductService
    data = await state.get_data()
    variant = await sync_to_async(
        lambda: ProductVariant.objects.select_related('product').get(id=data['variant_id'])
    )()
    quantity = data['quantity']

    try:
        await sync_to_async(ProductService.restock)(variant, quantity)
        await sync_to_async(variant.refresh_from_db)()
        await callback.message.edit_text(
            f"✅ *Kirim qayd etildi!*\n\n"
            f"📦 {variant.product.name} — {variant.name}\n"
            f"➕ Keldi: *{quantity}* dona\n"
            f"📊 Omborda jami: *{variant.quantity}* dona"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Xato: {str(e)}")

    await state.clear()


# Debt callback handlers
@router.callback_query(VoiceDebtState.waiting_customer, F.data.startswith("vd_select_customer_"))
async def voice_debt_customer_chosen(callback: CallbackQuery, state: FSMContext):
    customer_id = callback.data.replace("vd_select_customer_", "")
    customer = await sync_to_async(Customer.objects.get)(id=customer_id)
    data = await state.get_data()
    amount = data['amount']
    await state.update_data(customer_id=customer_id)
    await state.set_state(VoiceDebtState.waiting_confirm)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="vd_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
        ]
    ])
    await callback.message.edit_text(
        f"👤 *Qarzni tasdiqlaysizmi?*\n\n"
        f"👤 Mijoz: *{customer.name}*\n"
        f"💰 Summa: *{amount:,}* so'm",
        reply_markup=markup
    )


@router.callback_query(VoiceDebtState.waiting_customer, F.data == "vd_create_customer")
async def voice_debt_create_customer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    customer_name = data['customer_name']
    amount = data['amount']

    customer = await sync_to_async(Customer.objects.create)(
        store=store,
        name=customer_name,
    )
    await state.update_data(customer_id=str(customer.id))
    await state.set_state(VoiceDebtState.waiting_confirm)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="vd_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="voice_cancel")
        ]
    ])
    await callback.message.edit_text(
        f"👤 Yangi mijoz yaratildi: *{customer.name}*\n\n"
        f"💰 Qarz yozilsinmi?\n"
        f"💰 Summa: *{amount:,}* so'm",
        reply_markup=markup
    )


@router.callback_query(VoiceDebtState.waiting_confirm, F.data == "vd_confirm")
async def voice_debt_confirmed(callback: CallbackQuery, state: FSMContext):
    from apps.debts.models import Debt
    data = await state.get_data()
    store = await sync_to_async(Store.objects.get)(id=data['store_id'])
    customer = await sync_to_async(Customer.objects.get)(id=data['customer_id'])
    amount = data['amount']

    try:
        await sync_to_async(Debt.objects.create)(
            customer=customer,
            store=store,
            amount=amount,
        )
        await callback.message.edit_text(
            f"✅ *Qarz qayd etildi!*\n\n"
            f"👤 Mijoz: *{customer.name}*\n"
            f"💰 Summa: *{amount:,}* so'm"
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Xato: {str(e)}")

    await state.clear()


async def _complete_voice_sale(event, state, store, variant, quantity, payment_type, customer=None):
    from apps.sales.services import SaleService
    import django.utils.timezone as tz

    try:
        sale = await sync_to_async(SaleService.create_sale)(
            store=store,
            items=[{'variant': variant, 'quantity': quantity}],
            payment_type=payment_type,
            customer=customer,
        )

        variant_updated = await sync_to_async(
            lambda: ProductVariant.objects.get(id=variant.id)
        )()

        warning = ""
        if variant_updated.quantity <= variant_updated.min_threshold:
            warning = f"\n\n⚠️ *Diqqat! Mahsulot kam qoldi!*\nMinimal chegara: {variant_updated.min_threshold} dona"

        text = (
            f"✅ *Sotuv qayd etildi!*\n\n"
            f"📦 {variant.product.name} — {variant.name}\n"
            f"🔢 Miqdor: *{quantity}* dona\n"
            f"💰 Summa: *{sale.total:,}* so'm\n"
            f"💳 To'lov: *{sale.get_payment_type_display()}*\n"
            f"{customer_text}"
            f"📊 Omborda qoldi: *{variant_updated.quantity}* dona\n"
            f"🕐 Vaqt: *{now}*"
            f"{warning}"
        )

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
        else:
            await event.answer(text)

    except ValidationError as e:
        error_text = f"❌ Xato: {e.message}"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(error_text)
        else:
            await event.answer(error_text)

    await state.clear()