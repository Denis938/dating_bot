# Dating Bot 💕

Современный дейтинг-бот с поддержкой Telegram и Web интерфейса.

## 📋 О проекте

Dating Bot — это платформа для знакомств с умным алгоритмом подбора пар, реализованная как модульный монолит на Python (FastAPI).

### Ключевые возможности

- 🔐 **Аутентификация** через Telegram и Email
- 👤 **Профили пользователей** с фото и предпочтениями
- 💘 **Умный matching** с учётом геолокации и предпочтений
- 💬 **Чат** в реальном времени (WebSocket)
- 📸 **Медиа** с хранением в S3

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Dating Bot System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Clients:                                                   │
│  ┌─────────────┐          ┌─────────────┐                  │
│  │ Telegram    │          │ Web App     │                  │
│  │ Bot         │          │ (React)     │                  │
│  └──────┬──────┘          └──────┬──────┘                  │
│         │                        │                          │
│         └────────────┬───────────┘                          │
│                      │                                       │
│                      ▼                                       │
│         ┌────────────────────────┐                          │
│         │   FastAPI Backend      │                          │
│         │                        │                          │
│         │ ┌────┐ ┌────┐ ┌────┐  │                          │
│         │ │Auth│ │Match│ │Chat│  │                          │
│         │ └────┘ └────┘ └────┘  │                          │
│         └───────────┬────────────┘                          │
│                     │                                        │
│    ┌────────────────┼────────────────┐                      │
│    │                │                │                      │
│    ▼                ▼                ▼                      │
│ ┌────────┐   ┌──────────┐   ┌──────────┐                   │
│ │Postgres│   │  Redis   │   │   S3     │                   │
│ └────────┘   └──────────┘   └──────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Сервисы

| Сервис | Описание | Статус |
|--------|----------|--------|
| **Auth Service** | Аутентификация, JWT токены | 🟢 MVP |
| **Profile Service** | Управление профилем и фото | 🟢 MVP |
| **Matching Service** | Алгоритм подбора пар | 🟢 MVP |
| **Chat Service** | Сообщения в реальном времени | 🟢 MVP |
| **Media Service** | Загрузка и хранение файлов | 🟢 MVP |
| **Notification Service** | Уведомления | ⏭️ Phase 2 |

---

## 🛠 Технологический стек

### Backend
- **Python 3.11+**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** — ORM (async)
- **Alembic** — миграции БД
- **Pydantic v2** — валидация данных

### Базы данных и хранилища
- **PostgreSQL 15+** — основная БД
- **Redis 7+** — кеш, сессии, очереди
- **MinIO / S3** — объектное хранилище

### Клиенты
- **aiogram 3.x** — Telegram Bot
- **React + TypeScript** — Web App (опционально)
- **WebSocket** — realtime сообщения

### Infrastructure
- **Docker & Docker Compose**
- **Nginx** — reverse proxy

---

## 📁 Структура проекта

```
dating-bot/
│
├── backend/
│   ├── src/
│   │   ├── main.py              # Точка входа
│   │   ├── config.py            # Конфигурация
│   │   ├── database.py          # DB connection
│   │   │
│   │   └── modules/
│   │       ├── auth/            # Auth Service
│   │       ├── profile/         # Profile Service
│   │       ├── matching/        # Matching Service
│   │       ├── chat/            # Chat Service
│   │       └── media/           # Media Service
│   │
│   ├── db/
│   │   ├── migrations/          # Alembic migrations
│   │   └── seeds/               # Test data
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── bot/
│   ├── main.py                  # Telegram bot
│   ├── handlers/
│   └── Dockerfile
│
├── docs/
│   ├── services.md              # Описание сервисов
│   ├── architecture.md          # Архитектура
│   └── db_schema.md             # Схема БД
│
├── diagrams/                    # Диаграммы
├── docker-compose.yml
└── README.md
```

---

## 🚀 Быстрый старт

### Требования

- Docker & Docker Compose
- Python 3.11+ (для локальной разработки)

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/dating-bot.git
cd dating-bot
```

### 2. Настройка переменных окружения

```bash
# Скопируйте пример
cp backend/.env.example backend/.env

# Отредактируйте значения
# DATABASE_URL, JWT_SECRET, TELEGRAM_BOT_TOKEN, etc.
```

### 3. Запуск через Docker Compose

```bash
# Development режим
docker-compose -f docker-compose.dev.yml up --build

# Production режим
docker-compose up -d
```

### 4. Применение миграций

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Проверка

- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MinIO Console**: http://localhost:9001

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [Описание сервисов](./docs/services.md) | Детальное описание каждого сервиса |
| [Архитектура](./docs/architecture.md) | Архитектурные решения и схемы |
| [Схема БД](./docs/db_schema.md) | ER-диаграмма и SQL скрипты |

---

## 🔌 API Endpoints

### Auth
```
POST /auth/register          # Регистрация
POST /auth/login             # Вход
POST /auth/logout            # Выход
POST /auth/refresh           # Обновление токена
POST /auth/telegram/init     # Telegram auth
```

### Profile
```
GET  /profile/me             # Мой профиль
PUT  /profile/me             # Обновить профиль
POST /profile/photo          # Загрузить фото
GET  /profile/preferences    # Предпочтения
PUT  /profile/preferences    # Обновить предпочтения
```

### Matching
```
GET  /matching/recommendations    # Рекомендации
POST /matching/like               # Лайк
POST /matching/dislike            # Дизлайк
GET  /matching/matches            # Список матчей
```

### Chat
```
GET  /chat/:match_id/messages    # История сообщений
POST /chat/:match_id/messages    # Отправить сообщение
WS   /chat/ws                     # WebSocket
```

---

## 🧪 Тестирование

```bash
# Запустить все тесты
docker-compose exec backend pytest

# Запустить с покрытием
docker-compose exec backend pytest --cov=src

# Конкретный тест
docker-compose exec backend pytest tests/test_matching.py
```

---

## 🔐 Безопасность

- ✅ HTTPS для всех соединений
- ✅ JWT токены (access + refresh)
- ✅ Пароли: bcrypt с salt
- ✅ Rate limiting на критичных endpoints
- ✅ Валидация входных данных
- ✅ SQL injection защита (ORM)

---

## 📈 Масштабирование

### Текущая архитектура (MVP)
- Модульный монолит
- Вертикальное масштабирование

### Будущая архитектура
- Выделение сервисов в микросервисы
- Горизонтальное масштабирование
- Redis Cluster
- PostgreSQL репликация

---

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📝 License

MIT License — см. [LICENSE](LICENSE) файл

---

## 📞 Контакты

- **Telegram**: @yourusername
- **Email**: your@email.com

---

## 🗺 Roadmap

### Phase 1 (MVP) ✅
- [x] Проектирование архитектуры
- [x] Схема базы данных
- [ ] Auth Service
- [ ] Profile Service
- [ ] Matching Service
- [ ] Chat Service
- [ ] Media Service

### Phase 2
- [ ] Notification Service
- [ ] Premium подписки
- [ ] Расширенная аналитика
- [ ] Mobile app

### Phase 3
- [ ] AI-based matching
- [ ] Video calls
- [ ] Events и встречи

---

## ⭐ Acknowledgments

- FastAPI — современный веб-фреймворк
- aiogram — лучшая библиотека для Telegram ботов
- SQLAlchemy — мощная ORM

---

<div align="center">

**Made with ❤️ for dating**

[🔝 Back to top](#dating-bot-)

</div>
