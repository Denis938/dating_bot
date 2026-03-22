# Описание сервисов Dating Bot

## Обзор

Данный документ описывает сервисы системы дейтинг-бота. Архитектура построена по принципу **модульного монолита** с четким разделением ответственности.

---

## 1. Auth Service (Аутентификация)

### Ответственность
- Регистрация пользователей (Telegram / Email)
- Аутентификация и авторизация
- Управление сессиями и токенами
- Восстановление доступа

### API
```
POST /auth/register          # Регистрация
POST /auth/login             # Вход
POST /auth/logout            # Выход
POST /auth/refresh           # Обновление токена
POST /auth/telegram/init     # Инициализация Telegram auth
```

### Зависимости
- PostgreSQL (users table)
- Redis (сессии, rate limiting)

### Модели данных
```
User:
  - id: UUID
  - telegram_id: string (unique, nullable)
  - email: string (unique, nullable)
  - password_hash: string
  - is_active: boolean
  - created_at: timestamp
  - updated_at: timestamp
```

---

## 2. User Profile Service (Профиль пользователя)

### Ответственность
- Управление анкетой пользователя
- Загрузка и управление фото
- Предпочтения по поиску
- Геолокация

### API
```
GET  /profile/me             # Получить свой профиль
PUT  /profile/me             # Обновить профиль
POST /profile/photo          # Загрузить фото
DELETE /profile/photo/:id    # Удалить фото
GET  /profile/preferences    # Получить предпочтения
PUT  /profile/preferences    # Обновить предпочтения
GET  /profile/:id            # Получить профиль другого пользователя
```

### Зависимости
- Auth Service
- Media Service
- PostgreSQL (profiles, preferences, photos)

### Модели данных
```
Profile:
  - id: UUID
  - user_id: UUID (FK -> User)
  - name: string
  - age: integer
  - bio: text
  - gender: enum (male, female, other)
  - orientation: enum (straight, gay, lesbian, bi)
  - created_at: timestamp

Preferences:
  - user_id: UUID (FK -> User, PK)
  - preferred_gender: array[enum]
  - age_min: integer
  - age_max: integer
  - radius_km: integer

Photo:
  - id: UUID
  - user_id: UUID (FK -> User)
  - url: string
  - is_main: boolean
  - sort_order: integer
```

---

## 3. Matching Service (Подбор пар - ЯДРО)

### Ответственность
- Алгоритм рекомендаций
- Обработка лайков/дизлайков
- Создание матчей при взаимной симпатии
- Фильтрация по предпочтениям

### API
```
GET  /matching/recommendations    # Получить рекомендации
POST /matching/like               # Лайкнуть пользователя
POST /matching/dislike            # Дизлайкнуть
POST /matching/superlike          # Супер-лайк
GET  /matching/matches            # Список матчей
GET  /matching/matches/:id        # Конкретный матч
```

### Зависимости
- User Profile Service
- PostgreSQL (likes, matches)
- Redis (кеш рекомендаций)

### Модели данных
```
Like:
  - id: UUID
  - from_user_id: UUID (FK -> User)
  - to_user_id: UUID (FK -> User)
  - type: enum (like, dislike, superlike)
  - created_at: timestamp
  - UNIQUE(from_user_id, to_user_id)

Match:
  - id: UUID
  - user1_id: UUID (FK -> User)
  - user2_id: UUID (FK -> User)
  - created_at: timestamp
  - is_active: boolean
```

### Алгоритм подбора
1. Фильтрация по полу и ориентации
2. Фильтрация по возрастному диапазону
3. Геолокация (радиус)
4. Исключение уже просмотренных
5. Сортировка по релевантности (online, активность, рейтинг)

---

## 4. Chat Service (Чат)

### Ответственность
- Переписка между пользователями в матче
- Хранение истории сообщений
- Real-time доставка (WebSocket)
- Статусы (прочитано, печатает)

### API
```
GET  /chat/:match_id/messages    # История сообщений
POST /chat/:match_id/messages    # Отправить сообщение
WS /chat/ws                      # WebSocket подключение
```

### WebSocket события
```
Client -> Server:
  - message:send { match_id, text }
  - message:read { match_id, message_id }
  - typing:start { match_id }
  - typing:stop { match_id }

Server -> Client:
  - message:new { id, match_id, sender_id, text, created_at }
  - message:read { match_id, message_id }
  - typing:update { match_id, user_id, is_typing }
```

### Зависимости
- Matching Service (проверка матча)
- PostgreSQL (messages)
- Redis (Pub/Sub для WebSocket)

### Модели данных
```
Message:
  - id: UUID
  - match_id: UUID (FK -> Match)
  - sender_id: UUID (FK -> User)
  - text: text
  - is_read: boolean
  - created_at: timestamp
```

---

## 5. Media Service (Медиа)

### Ответственность
- Загрузка файлов (фото)
- Хранение в Object Storage (S3)
- Генерация превью
- Валидация контента

### API
```
POST /media/upload             # Загрузить файл
GET  /media/:id                # Получить файл
DELETE /media/:id              # Удалить файл
```

### Зависимости
- S3-compatible storage (MinIO / AWS S3)
- Image processing (Pillow / sharp)

### Хранение
```
Bucket structure:
  dating-bot/
    profiles/
      :user_id/
        :photo_id_original.jpg
        :photo_id_thumb.jpg
```

---

## 6. Notification Service (Уведомления)

### Ответственность
- Push-уведомления о новых матчах
- Уведомления о сообщениях
- Email рассылки
- Telegram уведомления

### API
```
POST /notify/push              # Отправить push
POST /notify/email             # Отправить email
POST /notify/telegram          # Отправить в Telegram
```

### События для уведомлений
- `match.new` - Новый матч
- `message.new` - Новое сообщение
- `like.received` - Получен лайк

### Зависимости
- Redis (очереди задач)
- Telegram Bot API
- SMTP server / SendGrid

---

## Схема взаимодействия сервисов

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│         Telegram Bot API        │      Web App (React)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│              (FastAPI + Middleware)                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│ Auth Service  │   │ Profile Service │   │ Match Service │
└───────────────┘   └─────────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Chat Service   │
                    └─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  PostgreSQL   │   │     Redis       │   │  Media (S3)   │
└───────────────┘   └─────────────────┘   └───────────────┘
```

---

## MVP Scope (Минимальная версия)

Для первой версии реализуем:

| Сервис | Статус |
|--------|--------|
| Auth Service | ✅ MVP |
| Profile Service | ✅ MVP |
| Matching Service | ✅ MVP |
| Chat Service | ✅ MVP |
| Media Service | ✅ MVP (базовый) |
| Notification Service | ⏭️ Phase 2 |
