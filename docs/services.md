# Описание сервисов

## 1. Auth Service

**Задачи:**
- Регистрация через Telegram
- JWT токены

**API:**
```
POST /auth/register
POST /auth/login
```

---

## 2. Profile Service

**Задачи:**
- Анкета (имя, возраст, био, фото)
- Предпочтения (кого ищет, возраст, радиус)

**API:**
```
GET  /profile/me
PUT  /profile/me
GET  /profile/preferences
PUT  /profile/preferences
```

---

## 3. Matching Service

**Задачи:**
- Рекомендации пользователей
- Лайки / дизлайки
- Создание мэтчей

**API:**
```
GET  /matching/recommendations
POST /matching/like
POST /matching/dislike
GET  /matching/matches
```

---

## 4. Chat Service

**Задачи:**
- Переписка между матчами
- Хранение сообщений

**API:**
```
GET  /chat/:match_id/messages
POST /chat/:match_id/messages
```

---

## 5. Media Service

**Задачи:**
- Загрузка фото
- Хранение в S3

**API:**
```
POST /media/upload
GET  /media/:id
```
