# Google Sheets CRM Setup

## Что нужно сделать

### 1. Создайте проект в Google Cloud
- Откройте Google Cloud Console.
- Создайте новый проект.
- Включите Google Sheets API.

### 2. Создайте service account
- Создайте service account.
- Скачайте JSON-ключ.
- Сохраните его как секретный файл.

### 3. Поделитесь таблицей
- Откройте вашу Google Sheets.
- Нажмите Share.
- Добавьте email service account из JSON-файла.
- Дайте доступ Editor.

### 4. Подготовьте лист
Создайте лист с названием:
`Orders`

Добавьте заголовки в первую строку:

created_at | full_name | username | phone | address | items | total | user_id

### 5. Добавьте переменные в Replit
- BOT_TOKEN
- ADMIN_IDS
- GOOGLE_SHEET_ID
- GOOGLE_CREDS_JSON
- CHANNEL_USERNAME
- SITE_URL

### 6. Проверка
Запустите бота и оформите тестовый заказ.
Если всё сделано правильно, новая строка появится в листе Orders.