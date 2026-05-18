import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from typing import Dict, List, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    filters,
)

from catalog import (
    load_products,
    get_categories,
    get_products_by_category,
    get_product_by_id,
    format_price,
)
from sheets import append_order_to_sheet
from stars_payments import create_stars_invoice, handle_successful_payment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@beautysupplyshop")
SITE_URL = os.getenv("SITE_URL", "https://beauty-supply.shop")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

PRODUCTS = load_products("products_catalog.json")
CARTS: Dict[int, List[int]] = {}
USER_STATE: Dict[int, Dict[str, Any]] = {}

CATEGORY_LABELS = {
    "Skincare": "Skincare (Уход за кожей)",
    "SPF": "SPF (Солнцезащита)",
    "Haircare": "Haircare (Уход за волосами)",
    "Bodycare": "Bodycare (Уход за телом)",
}


def ensure_user_state(user_id: int):
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {"step": None, "draft": {}}


def get_cart_total(cart_ids: List[int]) -> int:
    products = [p for p in PRODUCTS if p["id"] in cart_ids]
    return sum(p["price"] for p in products)


def get_cart_products(cart_ids: List[int]):
    return [p for p in PRODUCTS if p["id"] in cart_ids]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_state(user.id)

    text = (
        f"🌸 Добро пожаловать в BEAUTY SUPPLY SHOP, {user.first_name}!\n\n"
        "🇺🇸🇫🇷🇰🇷 Оригинальная косметика из США, Европы и Кореи\n"
        "💎 Подборка средств для skincare, haircare, bodycare и SPF\n"
        "🚚 Доставка по России\n"
        "⭐ Оплата Telegram Stars доступна для digital-товаров\n\n"
        f"📢 Канал: {CHANNEL_USERNAME}\n"
        f"🌐 Сайт: {SITE_URL}\n\n"
        "Выберите действие:"
    )

    keyboard = [
        [InlineKeyboardButton("🛍️ Каталог", callback_data="catalog")],
        [InlineKeyboardButton("🔥 Хиты продаж", callback_data="bestsellers")],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart")],
        [InlineKeyboardButton("⭐ Оплата Stars", callback_data="stars_info")],
        [InlineKeyboardButton("📦 Как заказать", callback_data="how_to_order")],
        [InlineKeyboardButton("💬 Контакты", callback_data="contact")],
    ]

    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    ensure_user_state(user_id)

    if data == "catalog":
        await show_categories(query)
    elif data == "bestsellers":
        await show_bestsellers(query)
    elif data == "cart":
        await show_cart(query)
    elif data == "how_to_order":
        await show_how_to_order(query)
    elif data == "contact":
        await show_contact(query)
    elif data == "stars_info":
        await show_stars_info(query)
    elif data == "checkout":
        await checkout(query, context)
    elif data == "back_main":
        await back_to_main(query)
    elif data == "clear_cart":
        CARTS[user_id] = []
        await query.answer("Корзина очищена", show_alert=True)
        await show_cart(query)
    elif data.startswith("cat_"):
        await show_products_by_category(query, data.replace("cat_", ""))
    elif data.startswith("prod_"):
        await show_product_detail(query, int(data.replace("prod_", "")))
    elif data.startswith("add_"):
        await add_to_cart(query, int(data.replace("add_", "")))
    elif data.startswith("buy_stars_"):
        payload = data.replace("buy_stars_", "")
        await create_stars_invoice(query, context, payload)


async def show_categories(query):
    categories = get_categories(PRODUCTS)
    keyboard = [[InlineKeyboardButton(CATEGORY_LABELS.get(c, c), callback_data=f"cat_{c}")] for c in categories]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])

    await query.edit_message_text(
        "📂 Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_products_by_category(query, category):
    products = get_products_by_category(PRODUCTS, category)

    if not products:
        await query.edit_message_text(
            "В этой категории пока нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад к категориям", callback_data="catalog")]
            ])
        )
        return

    keyboard = []
    for p in products:
        status = "✅" if p["in_stock"] else "⏳"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {p['brand']} — {format_price(p['price'])} ₽",
                callback_data=f"prod_{p['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад к категориям", callback_data="catalog")])

    await query.edit_message_text(
        f"🛍️ Категория: {category}\n\nВыберите товар:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_product_detail(query, product_id):
    p = get_product_by_id(PRODUCTS, product_id)
    if not p:
        await query.edit_message_text("❌ Товар не найден")
        return

    status = "✅ В наличии" if p["in_stock"] else "⏳ Под заказ (7–14 дней)"
    text = (
        f"🛍️ {p['name']}\n\n"
        f"🏷️ Бренд: {p['brand']}\n"
        f"🌍 Страна: {p['country']}\n"
        f"💰 Цена: {format_price(p['price'])} ₽\n"
        f"📦 Статус: {status}\n\n"
        f"📝 Описание:\n{p['description']}\n\n"
        f"✨ Эффект:\n{p['benefits']}\n\n"
        f"👤 Для кого:\n{p['for_whom']}"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_{p['id']}")],
        [InlineKeyboardButton("⭐ Купить за Stars", callback_data=f"buy_stars_{p['id']}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{p['category']}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def add_to_cart(query, product_id: int):
    user_id = query.from_user.id
    CARTS.setdefault(user_id, [])

    if product_id not in CARTS[user_id]:
        CARTS[user_id].append(product_id)
        await query.answer("✅ Товар добавлен в корзину!", show_alert=True)
    else:
        await query.answer("ℹ️ Товар уже в корзине", show_alert=True)


async def show_cart(query):
    user_id = query.from_user.id
    cart_ids = CARTS.get(user_id, [])

    if not cart_ids:
        await query.edit_message_text(
            "🛒 Ваша корзина пуста.\n\nДобавьте товары из каталога.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Перейти в каталог", callback_data="catalog")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
            ])
        )
        return

    cart_products = get_cart_products(cart_ids)
    total = get_cart_total(cart_ids)

    text = "🛒 Ваша корзина:\n\n"
    for i, p in enumerate(cart_products, 1):
        text += f"{i}. {p['brand']} {p['name']} — {format_price(p['price'])} ₽\n"

    text += f"\n💰 Итого: {format_price(total)} ₽"

    keyboard = [
        [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton("🧹 Очистить корзину", callback_data="clear_cart")],
        [InlineKeyboardButton("🛍️ Продолжить покупки", callback_data="catalog")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def clear_cart(query):
    user_id = query.from_user.id
    CARTS[user_id] = []
    await query.answer("Корзина очищена", show_alert=True)
    await show_cart(query)


async def checkout(query, context):
    user_id = query.from_user.id
    cart_ids = CARTS.get(user_id, [])

    if not cart_ids:
        await query.answer("Корзина пуста", show_alert=True)
        return

    cart_products = get_cart_products(cart_ids)
    total = get_cart_total(cart_ids)

    draft = {
        "user_id": user_id,
        "username": query.from_user.username or "",
        "full_name": f"{query.from_user.first_name or ''} {query.from_user.last_name or ''}".strip(),
        "items": [p["name"] for p in cart_products],
        "total": total,
        "created_at": datetime.utcnow().isoformat()
    }

    USER_STATE[user_id]["draft"] = draft
    USER_STATE[user_id]["step"] = "ask_phone"

    text = (
        "✅ Оформление заказа\n\n"
        f"Сумма: {format_price(total)} ₽\n\n"
        "Отправьте, пожалуйста, ваш номер телефона одним сообщением."
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
        ])
    )


async def show_how_to_order(query):
    text = (
        "📦 Как сделать заказ:\n\n"
        "1. Выберите товары из каталога\n"
        "2. Добавьте их в корзину\n"
        "3. Нажмите «Оформить заказ»\n"
        "4. Отправьте телефон и адрес\n"
        "5. Подтвердите оплату\n\n"
        "💳 Оплата: карта, СБП\n"
        "⭐️ Telegram Stars\n"
        "🚚 Доставка: СДЭК, Boxberry, Почта России\n\n"
        "По всем вопросам пишите администраторам:\n"
        "@miss_srt8\n"
        "@Man_GPT"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
        ])
    )


async def show_contact(query):
    text = (
        "💬 Контакты:\n\n"
        f"📢 Канал: {CHANNEL_USERNAME}\n"
        f"🌐 Сайт: {SITE_URL}\n\n"
        "👩‍💼 Администраторы:\n"
        "• @miss_srt8\n"
        "• @Man_GPT\n\n"
        "Для оформления и вопросов напишите менеджеру или используйте кнопки бота."
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
        ])
    )


async def show_stars_info(query):
    text = (
        "⭐ Telegram Stars\n\n"
        "Совершайте покупки за считанные секунды через ⭐ Telegram Stars ⭐ — самый быстрый, удобный и безопасный способ оплаты в 2026г.\n"
        "В нашем магазине вы полностью защищены от рисков: мы предоставляем 14 дней на возврат или замену товаров за теплый отзыв о нашей компании 🤗❤️"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ Каталог", callback_data="catalog")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
        ])
    )


async def show_bestsellers(query):
    products = [p for p in PRODUCTS if p["in_stock"]][:5]
    keyboard = []
    for p in products:
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {p['name']} — {format_price(p['price'])} ₽",
                callback_data=f"prod_{p['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")])

    await query.edit_message_text(
        "🔥 Хиты продаж:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_to_main(query):
    user = query.from_user
    text = (
        f"🌸 BEAUTY SUPPLY SHOP, {user.first_name}!\n\n"
        "🇺🇸🇫🇷🇰🇷 Оригинальная косметика из США, Европы и Кореи\n"
        "💎 Каталог, корзина, заказы, Stars\n\n"
        f"📢 Канал: {CHANNEL_USERNAME}\n"
        f"🌐 Сайт: {SITE_URL}"
    )

    keyboard = [
        [InlineKeyboardButton("🛍️ Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton("🔥 Хиты продаж", callback_data="bestsellers")],
        [InlineKeyboardButton("🛒 Моя корзина", callback_data="cart")],
        [InlineKeyboardButton("⭐ Оплата Stars", callback_data="stars_info")],
        [InlineKeyboardButton("📦 Как заказать", callback_data="how_to_order")],
        [InlineKeyboardButton("💬 Контакты", callback_data="contact")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user_state(user_id)
    step = USER_STATE[user_id]["step"]
    text = update.message.text.strip()

    if step == "ask_phone":
        USER_STATE[user_id]["draft"]["phone"] = text
        USER_STATE[user_id]["step"] = "ask_address"
        await update.message.reply_text("Теперь отправьте город и адрес доставки.")
        return

    if step == "ask_address":
        draft = USER_STATE[user_id]["draft"]
        draft["address"] = text
        USER_STATE[user_id]["step"] = None

        order_text = (
            "🧾 Новый заказ\n\n"
            f"Имя: {draft.get('full_name', '')}\n"
            f"Username: @{draft.get('username', '')}\n"
            f"Телефон: {draft.get('phone', '')}\n"
            f"Адрес: {draft.get('address', '')}\n"
            f"Товары: {', '.join(draft.get('items', []))}\n"
            f"Сумма: {format_price(draft.get('total', 0))} ₽\n"
            f"Время: {datetime.utcnow().isoformat()}"
        )

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=order_text)
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin_id}: {e}")

        if GOOGLE_SHEET_ID:
            try:
                append_order_to_sheet(draft, GOOGLE_SHEET_ID, GOOGLE_CREDS_JSON)
            except Exception as e:
                logger.warning(f"Google Sheets append failed: {e}")

        CARTS[user_id] = []
        await update.message.reply_text(
            "✅ Спасибо! Заказ принят. Менеджер свяжется с вами в ближайшее время."
        )
        return

    await update.message.reply_text("Используйте кнопки меню /start")


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_successful_payment(update, context, ADMIN_IDS)


def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    return app


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")
    app = build_app()
    logger.info("BOT STARTED")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()