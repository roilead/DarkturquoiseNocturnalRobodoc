# BEAUTY SUPPLY SHOP

Telegram commerce bot for beauty products.

## Запуск в Replit

1. Создайте новый Python Repl.
2. Добавьте файлы из этого проекта.
3. Создайте `.env` и заполните переменные:
   - BOT_TOKEN
   - CHANNEL_USERNAME
   - SITE_URL
   - ADMIN_IDS
   - GOOGLE_SHEET_ID
   - GOOGLE_CREDS_JSON
4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
5. Запустите:
   ```bash
   python bot.py
   ```

## Что умеет бот

- Каталог товаров.
- Карточки товаров.
- Корзина.
- Оформление заказа.
- Уведомления двум администраторам.
- Интеграция с Google Sheets.
- Telegram Stars flow для digital-оферов.

  ## Структура проекта
main.py
catalog.py
sheets.py
stars_payments.py
products_catalog.json
requirements.txt
README.md
google_setup.md