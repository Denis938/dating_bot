# Dating Bot

Telegram дейтинг-бот с подбором пар.

## Документация

Вся документация находится в папке **DOCS/**

### 📁 Структура документации

```
DOCS/
├── README.md          # Полное описание архитектуры (Этап 1)
└── image-1.png        # Схема базы данных
```

## Этапы разработки

### ✅ Этап 1: Планирование и проектирование

- [x] Описание сервисов
- [x] Архитектурная схема
- [x] Схема данных (PostgreSQL + SurrealDB)

**Подробности:** [DOCS/README.md](./DOCS/README.md)

### ⏳ Этап 2: Реализация

- [ ] Bot Service (aiogram 3.x)
- [ ] Profile Service (FastAPI)
- [ ] Matching Service (FastAPI)
- [ ] Celery Workers
- [ ] Admin Service

### ⏳ Этап 3: Инфраструктура

- [ ] Docker Compose
- [ ] CI/CD (GitHub Actions)
- [ ] Prometheus + Grafana

## Стек технологий

| Технология | Назначение |
|------------|------------|
| Python, aiogram 3.x | Bot Service |
| Python, FastAPI | REST API сервисы |
| PostgreSQL | Основная БД |
| SurrealDB | Граф взаимодействий |
| Redis | Кэш, rate-limit |
| Celery + RabbitMQ | Фоновые задачи |
| MinIO (S3) | Хранение фото |

## Быстрый старт

```bash
# Клонировать репозиторий
git clone <repo-url>
cd dating-bot

# Запустить (после реализации)
docker-compose up -d
```

## Лицензия

MIT
