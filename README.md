# Dating Bot 💕

Telegram дейтинг-бот с подбором пар.

## Стек

- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **Cache:** Redis
- **Storage:** S3 (MinIO)
- **Bot:** aiogram 3.x

## Структура

```
dating-bot/
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── modules/
│   │       ├── auth/
│   │       ├── profile/
│   │       ├── matching/
│   │       ├── chat/
│   │       └── media/
│   ├── db/migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── bot/
│   └── main.py
├── docs/
├── docker-compose.yml
└── README.md
```

## Быстрый старт

1. Клонировать репо:
```bash
git clone <your-repo-url>
cd dating-bot
```

2. Настроить окружение:
```bash
cp backend/.env.example backend/.env
# Отредактировать TELEGRAM_BOT_TOKEN
```

3. Запустить:
```bash
docker-compose -f docker-compose.dev.yml up
```

4. Открыть API docs: http://localhost:8000/docs

## Документация

- [Описание сервисов](./docs/services.md)
- [Архитектура](./docs/architecture.md)
- [Схема БД](./docs/db_schema.md)

## API Endpoints

**Auth:**
- POST /auth/register
- POST /auth/login

**Profile:**
- GET /profile/me
- PUT /profile/me

**Matching:**
- GET /matching/recommendations
- POST /matching/like
- GET /matching/matches

**Chat:**
- GET /chat/:match_id/messages
- POST /chat/:match_id/messages

## Коммиты

```bash
git add .
git commit -m "feat: описание изменений"
git push
```
