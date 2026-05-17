# AVITO Marketolog Bot

**AVITO Marketolog Bot** — это Telegram-бот для маркетологов, работающих с клиентами на площадке Avito. Он помогает
управлять несколькими аккаунтами клиентов, отвечать на сообщения через шаблоны и получать уведомления о новых сообщениях
от клиентов.

## Основные возможности

- **Работа с чатами**: просмотр непрочитанных сообщений от клиентов, отправка ответов (в том числе с использованием
  шаблонов)
- **Управление аккаунтами**: подключение и отключение аккаунтов клиентов Avito через API
- **Редактор шаблонов**: создание, изменение и удаление шаблонных сообщений для быстрых ответов
- **Уведомления**: подписка на уведомления о новых сообщениях от клиентов с доставкой в Telegram
- **Webhook-сервер**: FastAPI-сервер для приёма уведомлений от Avito
- **Автоматический проброс портов**: интеграция с ngrok для публичного доступа к вебхукам

## Технологический стек

| Компонент       | Технология                                  |
|-----------------|---------------------------------------------|
| **Бот**         | aiogram 3.19.0 + Python 3.10+               |
| **Веб-сервер**  | FastAPI + Uvicorn                           |
| **База данных** | PostgreSQL 14.2 (через SQLAlchemy+asyncpg)  |
| **HTTP-клиент** | aiohttp, requests                           |
| **Миграции**    | SQLAlchemy (автоматическое создание таблиц) |
| **Тесты**       | pytest + pytest-asyncio                     |

Полный список зависимостей см. в [`requirements.txt`](requirements.txt).

## Быстрый старт

### Предварительные требования

- Python 3.10 или выше
- PostgreSQL 14.2
- Аккаунт разработчика Avito с полученными `client_id` и `client_secret` (базовый тариф)
- Telegram Bot Token (через [@BotFather](https://t.me/BotFather))

### Структура проекта:

```text
avito-marketolog-bot/
├── src/                          # Исходный код
│   ├── main.py                   # Точка входа
│   ├── bot.py                    # Основной бот (/start, /support)
│   ├── config.py                 # Конфигурация и FSM
│   ├── database.py               # CRUD для users, accounts, templates
│   ├── models.py                 # SQLAlchemy-модели
│   ├── avito.py                  # Клиент API Avito
│   ├── callbacks.py              # Callback-фабрики
│   ├── middlewares.py            # Мидлвары
│   ├── server_notifications.py   # FastAPI для вебхуков Avito
│   └── routers/                  # Роутеры команд
│       ├── accounts_manager.py
│       ├── chat_manager.py
│       ├── notifications.py
│       └── templates_editor.py
├── tests/                        # Тесты
├── .github/workflows/            # CI
├── requirements.txt
├── pytest.ini
├── .env.example
└── .gitignore
```

### Установка

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/Tribble58/avito-marketolog-bot.git
   cd avito-marketolog-bot
   ```

2. **Создайте и активируйте виртуальное окружение**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```
   
3. **Установите зависимости**
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Настройте переменные окружения**
   ```env
   TG_BOT_TOKEN=ваш_токен_основного_бота
   TG_BOT_NOTIFICATIONS_TOKEN=ваш_токен_бота_уведомлений
   PG_HOST=localhost
   PG_PORT=5432
   PG_DATABASE=avito_bot_db
   PG_USER=ваш_пользователь
   PG_PASSWORD=ваш_пароль
   AVITO_CLIENT_ID=ваш_client_id
   AVITO_CLIENT_SECRET=ваш_client_secret
   SERVER_URL=ваш_публичный_url_от_ngrok   # заполняется после запуска ngrok
   ```
   
5. **Настройка базы данных**
   ```bash
   createdb avito_bot_db
   ```
   
### Запуск
```bash
python src/main.py
```

### Тесты
```bash
pytest
```
