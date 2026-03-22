# Архитектура Dating Bot

## 1. Обзор

**Тип архитектуры:** Монолит

**Почему монолит:**
- Проще в разработке и деплое
- Не нужен orchestration
- Нет distributed transactions
- Легче тестировать

---

## 2. Технологический стек

```
Backend:  Python 3.11 + FastAPI
Database: PostgreSQL 15
Cache:    Redis 7
Storage:  S3 (MinIO)
Client:   Telegram Bot (aiogram 3.x)
```

---

## 3. Схема системы

```
┌─────────────────┐
│  Telegram Bot   │
│   (aiogram)     │
└────────┬────────┘
         │
         │ HTTPS
         ▼
┌─────────────────────────────────┐
│      FastAPI Backend            │
│                                 │
│  ┌───────────────────────────┐  │
│  │  Modules (в одном app):   │  │
│  │  - Auth                   │  │
│  │  - Profile                │  │
│  │  - Matching               │  │
│  │  - Chat                   │  │
│  │  - Media                  │  │
│  └───────────────────────────┘  │
└───────────────┬─────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│Postgres│ │ Redis  │ │  S3    │
│  :5432 │ │ :6379  │ │ :9000  │
└────────┘ └────────┘ └────────┘
```

---

## 4. Структура проекта

```
dating-bot/
│
├── backend/
│   ├── src/
│   │   ├── main.py              # Точка входа
│   │   ├── config.py            # Настройки
│   │   ├── database.py          # DB подключение
│   │   │
│   │   └── modules/
│   │       ├── auth/            # Аутентификация
│   │       ├── profile/         # Профили
│   │       ├── matching/        # Лайки/мэтчи
│   │       ├── chat/            # Чат
│   │       └── media/           # Фото
│   │
│   ├── db/
│   │   └── migrations/          # Alembic
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── bot/
│   └── main.py                  # Telegram bot
│
├── docs/
│   ├── services.md
│   ├── architecture.md
│   └── db_schema.md
│
├── docker-compose.yml
└── README.md
```

---

## 5. Модули (внутри одного приложения)

### Auth Module
- Регистрация через Telegram
- JWT токены

### Profile Module
- Анкета пользователя
- Предпочтения
- Фото

### Matching Module
- Лайки / дизлайки
- Создание мэтчей
- Рекомендации

### Chat Module
- Сообщения
- WebSocket для realtime

### Media Module
- Загрузка фото в S3

---

## 6. База данных

**Основная:** PostgreSQL 15

**Таблицы:**
- users
- profiles
- preferences
- likes
- matches
- messages
- photos

**Кеш:** Redis (сессии, rate limiting)

---

## 7. Запуск

```bash
# Development
docker-compose -f docker-compose.dev.yml up

# Production
docker-compose up -d
```

**API Docs:** http://localhost:8000/docs

---

## 8. MVP Scope

| Модуль | Статус |
|--------|--------|
| Auth | ✅ |
| Profile | ✅ |
| Matching | ✅ |
| Chat | ✅ |
| Media | ✅ |
