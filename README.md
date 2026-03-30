# Gmail Checker

Автоматическая проверка Gmail и отправка дейли-сводок через OpenClaw.

## Возможности

- 📧 IMAP подключение к Gmail
- 🔔 Проверка новых писем
- 📊 Дейли-сводки (последние 24 часа)
- 🤖 Интеграция с OpenClaw для отправки в Telegram
- 💾 Трекинг последнего прочитанного письма

## Установка

```bash
pip install anthropic requests
```

## Конфигурация

Переменные окружения:
```bash
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
ANTHROPIC_API_KEY=your_key
GATEWAY_TOKEN=your_gateway_token
```

## Gmail App Password

1. Включите 2FA в Google Account
2. Зайдите в Security → App passwords
3. Создайте новый app password для "Mail"
4. Используйте этот пароль в `GMAIL_APP_PASSWORD`

## Файлы

- `checker.py` — основной модуль проверки IMAP
- `run.py` — обёртка для запуска через OpenClaw
- `state.json` — хранит ID последнего прочитанного письма

## Запуск

```bash
# Ручной запуск
python3 run.py

# Через OpenClaw cron (каждый день в 06:00 MSK)
```

## Лицензия

MIT
