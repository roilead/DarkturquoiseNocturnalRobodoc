from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.constants import ParseMode

STARS_PRODUCTS = {
    "digital_bonus_1": {
        "title": "Digital Bonus Pack (Цифровой бонус-пак)",
        "description": "Цифровой бонус, доступный для оплаты Telegram Stars",
        "stars": 100
    },
    "digital_bonus_2": {
        "title": "Premium Beauty Guide (Премиум гайд по красоте)",
        "description": "Платный digital-гайд по подбору ухода",
        "stars": 250
    }
}


async def create_stars_invoice(query, context, payload: str):
    product = STARS_PRODUCTS.get(f"digital_{payload}")
    if not product:
        product = {
            "title": "Beauty Digital Product (Цифровой товар)",
            "description": "Цифровой товар для оплаты Stars",
            "stars": 100
        }

    prices = [LabeledPrice(label=product["title"], amount=product["stars"])]

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=product["title"],
        description=product["description"],
        payload=f"stars_{payload}",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Оплатить Stars", pay=True)]
        ])
    )


async def handle_successful_payment(update, context, admin_ids):
    message = update.message
    if not message or not message.successful_payment:
        return

    sp = message.successful_payment
    info = (
        "✅ Получена оплата Stars\n\n"
        f"Пользователь: {message.from_user.id}\n"
        f"Сумма: {sp.total_amount} XTR\n"
        f"Payload (Идентификатор): {sp.invoice_payload}\n"
        f"Charge ID (ID платежа): {sp.telegram_payment_charge_id}"
    )

    for admin_id in admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=info)
        except Exception:
            pass

    await message.reply_text("✅ Оплата принята. Спасибо!")