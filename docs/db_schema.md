# Схема базы данных (DB Schema)

## Обзор

Данный документ описывает структуру базы данных PostgreSQL для дейтинг-бота.

### Диаграмма связей (ER Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ER DIAGRAM                                        │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │    users     │
    │              │
    │ id           │◀────┐
    │ telegram_id  │     │
    │ email        │     │
    │ password_hash│     │
    │ is_active    │     │
    │ is_verified  │     │
    │ created_at   │     │
    │ updated_at   │     │
    └──────┬───────┘     │
           │ 1:1         │ 1:N
           │             │
           ▼             │
    ┌──────────────┐     │
    │   profiles   │     │
    │              │     │
    │ id           │     │
    │ user_id (FK) │─────┘
    │ name         │
    │ age          │
    │ bio          │
    │ gender       │
    │ orientation  │
    │ latitude     │
    │ longitude    │
    │ is_verified  │
    │ created_at   │
    └──────┬───────┘
           │
           │ 1:N
           │
    ┌──────▼───────────────────────────────┐
    │           preferences                │
    │                                      │
    │ user_id (FK) ────────────────────────┘
    │ preferred_genders (ARRAY)
    │ age_min
    │ age_max
    │ radius_km
    │ updated_at
    └──────────────────────────────────────┘


    ┌──────────────┐
    │    users     │◀─────────────────────────────┐
    └──────┬───────┘                              │
           │ 1:N                                  │
           │                                      │
           ▼                                      │
    ┌──────────────┐      ┌──────────────┐        │
    │    likes     │      │    likes     │────────┘
    │              │      │              │
    │ id           │      │ id           │
    │ from_user_id │─────▶│ to_user_id   │
    │ to_user_id   │      │ from_user_id │
    │ type         │      │ type         │
    │ created_at   │      │ created_at   │
    └──────┬───────┘      └──────────────┘
           │
           │ (при взаимном like)
           ▼
    ┌──────────────┐
    │   matches    │
    │              │
    │ id           │
    │ user1_id     │◀─────┐
    │ user2_id     │─────▶│  users (оба участника)
    │ created_at   │
    │ is_active    │
    └──────┬───────┘
           │
           │ 1:N
           │
           ▼
    ┌──────────────┐
    │  messages    │
    │              │
    │ id           │
    │ match_id (FK)│
    │ sender_id    │◀───── users
    │ text         │
    │ is_read      │
    │ created_at   │
    └──────────────┘


    ┌──────────────┐
    │    users     │
    └──────┬───────┘
           │ 1:N
           │
           ▼
    ┌──────────────┐
    │    photos    │
    │              │
    │ id           │
    │ user_id (FK) │
    │ url          │
    │ is_main      │
    │ sort_order   │
    │ created_at   │
    └──────────────┘
```

---

## Таблицы

### 1. users

Основная таблица пользователей.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id     BIGINT UNIQUE,
    email           VARCHAR(255) UNIQUE,
    password_hash   VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Триггер для updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| telegram_id | BIGINT | ID пользователя Telegram (nullable) |
| email | VARCHAR | Email для входа (nullable) |
| password_hash | VARCHAR | Хеш пароля (nullable для Telegram auth) |
| is_active | BOOLEAN | Активен ли аккаунт |
| is_verified | BOOLEAN | Подтвержден ли аккаунт |
| created_at | TIMESTAMPTZ | Дата создания |
| updated_at | TIMESTAMPTZ | Дата обновления |

---

### 2. profiles

Профиль пользователя с личной информацией.

```sql
CREATE TYPE gender_type AS ENUM ('male', 'female', 'other');
CREATE TYPE orientation_type AS ENUM ('straight', 'gay', 'lesbian', 'bi', 'pansexual');

CREATE TABLE profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    age             INTEGER NOT NULL CHECK (age >= 18),
    bio             TEXT,
    gender          gender_type NOT NULL,
    orientation     orientation_type NOT NULL,
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_profiles_user_id ON profiles(user_id);
CREATE INDEX idx_profiles_gender ON profiles(gender);
CREATE INDEX idx_profiles_age ON profiles(age);
CREATE INDEX idx_profiles_location ON profiles USING GIST (
    ll_to_earth(latitude, longitude)
);

-- Composite index для matching
CREATE INDEX idx_profiles_gender_age ON profiles(gender, age);
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| user_id | UUID | Foreign key к users (1:1) |
| name | VARCHAR | Имя пользователя |
| age | INTEGER | Возраст (минимум 18) |
| bio | TEXT | Описание профиля |
| gender | ENUM | Пол пользователя |
| orientation | ENUM | Сексуальная ориентация |
| latitude | DECIMAL | Широта геолокации |
| longitude | DECIMAL | Долгота геолокации |
| is_verified | BOOLEAN | Подтвержденный профиль |
| created_at | TIMESTAMPTZ | Дата создания |

---

### 3. preferences

Предпочтения пользователя для подбора пар.

```sql
CREATE TABLE preferences (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_genders   gender_type[] NOT NULL DEFAULT '{}',
    age_min             INTEGER NOT NULL DEFAULT 18 CHECK (age_min >= 18),
    age_max             INTEGER NOT NULL DEFAULT 100 CHECK (age_max <= 100),
    radius_km           INTEGER NOT NULL DEFAULT 100 CHECK (radius_km >= 1),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_preferences_age_range ON preferences(age_min, age_max);

-- Триггер для updated_at
CREATE TRIGGER update_preferences_updated_at
    BEFORE UPDATE ON preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| user_id | UUID | Foreign key к users (1:1) |
| preferred_genders | ARRAY | Предпочтительные полы |
| age_min | INTEGER | Минимальный возраст |
| age_max | INTEGER | Максимальный возраст |
| radius_km | INTEGER | Радиус поиска в км |
| updated_at | TIMESTAMPTZ | Дата обновления |

---

### 4. likes

Лайки и дизлайки между пользователями.

```sql
CREATE TYPE like_type AS ENUM ('like', 'dislike', 'superlike');

CREATE TABLE likes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            like_type NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Уникальность: нельзя лайкнуть дважды
    CONSTRAINT unique_like UNIQUE (from_user_id, to_user_id),
    -- Нельзя лайкнуть себя
    CONSTRAINT different_users CHECK (from_user_id != to_user_id)
);

-- Индексы
CREATE INDEX idx_likes_from_user ON likes(from_user_id);
CREATE INDEX idx_likes_to_user ON likes(to_user_id);
CREATE UNIQUE INDEX idx_likes_from_to ON likes(from_user_id, to_user_id);
CREATE INDEX idx_likes_created_at ON likes(created_at);

-- Composite index для проверки взаимных лайков
CREATE INDEX idx_likes_mutual ON likes(from_user_id, to_user_id, type) 
    WHERE type IN ('like', 'superlike');
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| from_user_id | UUID | Кто лайкнул |
| to_user_id | UUID | Кого лайкнули |
| type | ENUM | Тип реакции (like/dislike/superlike) |
| created_at | TIMESTAMPTZ | Дата лайка |

---

### 5. matches

Взаимные симпатии (мэтчи).

```sql
CREATE TABLE matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Уникальность пары (порядок не важен)
    CONSTRAINT different_users CHECK (user1_id != user2_id),
    CONSTRAINT user_order CHECK (user1_id < user2_id)
);

-- Индексы
CREATE INDEX idx_matches_user1 ON matches(user1_id);
CREATE INDEX idx_matches_user2 ON matches(user2_id);
CREATE INDEX idx_matches_created_at ON matches(created_at);

-- Composite index для поиска матчей пользователя
CREATE INDEX idx_matches_user ON matches USING INDEX (user1_id, user2_id);

-- Функция для поиска матчей пользователя
CREATE OR REPLACE FUNCTION get_user_matches(p_user_id UUID)
RETURNS TABLE (
    match_id UUID,
    partner_id UUID,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        CASE WHEN m.user1_id = p_user_id THEN m.user2_id ELSE m.user1_id END,
        m.created_at
    FROM matches m
    WHERE (m.user1_id = p_user_id OR m.user2_id = p_user_id)
      AND m.is_active = TRUE;
END;
$$ LANGUAGE plpgsql;
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| user1_id | UUID | Первый пользователь (всегда меньший ID) |
| user2_id | UUID | Второй пользователь |
| created_at | TIMESTAMPTZ | Дата создания мэтча |
| is_active | BOOLEAN | Активен ли мэтч |

---

### 6. messages

Сообщения в чатах между матчами.

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Проверка что sender является участником матча
    CONSTRAINT sender_is_participant CHECK (
        EXISTS (
            SELECT 1 FROM matches 
            WHERE id = match_id 
              AND (user1_id = sender_id OR user2_id = sender_id)
        )
    )
);

-- Индексы
CREATE INDEX idx_messages_match_id ON messages(match_id);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_unread ON messages(match_id, is_read) WHERE is_read = FALSE;

-- Composite index для пагинации
CREATE INDEX idx_messages_match_created ON messages(match_id, created_at DESC);
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| match_id | UUID | Foreign key к matches |
| sender_id | UUID | Кто отправил сообщение |
| text | TEXT | Текст сообщения |
| is_read | BOOLEAN | Прочитано ли |
| created_at | TIMESTAMPTZ | Дата отправки |

---

### 7. photos

Фотографии пользователей.

```sql
CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url             VARCHAR(500) NOT NULL,
    is_main         BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_photos_user_id ON photos(user_id);
CREATE INDEX idx_photos_is_main ON photos(is_main);
CREATE INDEX idx_photos_sort_order ON photos(user_id, sort_order);

-- Триггер: только одно главное фото
CREATE OR REPLACE FUNCTION ensure_single_main_photo()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_main = TRUE THEN
        UPDATE photos 
        SET is_main = FALSE 
        WHERE user_id = NEW.user_id 
          AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_single_main_photo
    BEFORE INSERT OR UPDATE ON photos
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_main_photo();
```

**Описание полей:**
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Первичный ключ |
| user_id | UUID | Foreign key к users |
| url | VARCHAR | URL фотографии в S3 |
| is_main | BOOLEAN | Главное фото профиля |
| sort_order | INTEGER | Порядок сортировки |
| created_at | TIMESTAMPTZ | Дата загрузки |

---

### 8. sessions (опционально)

Сессии пользователей для управления токенами.

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token   VARCHAR(500) NOT NULL UNIQUE,
    device_info     VARCHAR(255),
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_refresh_token ON sessions(refresh_token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Автоудаление истекших сессий
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM sessions WHERE expires_at < NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Связи между таблицами

```
┌─────────────────────────────────────────────────────────────────┐
│                    TABLE RELATIONSHIPS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  users ──(1:1)──> profiles                                      │
│    │                    │                                       │
│    │                    └──(1:1)──> preferences                 │
│    │                                                            │
│    ├──(1:N)──> likes (as from_user)                             │
│    ├──(1:N)──> likes (as to_user)                               │
│    │                                                            │
│    ├──(1:N)──> matches (as user1)                               │
│    ├──(1:N)──> matches (as user2)                               │
│    │                                                            │
│    ├──(1:N)──> messages (as sender)                             │
│    │                                                            │
│    └──(1:N)──> photos                                           │
│                                                                 │
│  matches ──(1:N)──> messages                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## SQL-запросы для типовых операций

### 1. Получить рекомендации для пользователя

```sql
SELECT 
    p.id,
    p.name,
    p.age,
    p.bio,
    p.gender,
    ph.url as main_photo
FROM profiles p
LEFT JOIN photos ph ON ph.user_id = p.user_id AND ph.is_main = TRUE
LEFT JOIN preferences pref ON pref.user_id = :current_user_id
WHERE p.user_id != :current_user_id
  -- Пол соответствует предпочтениям
  AND p.gender = ANY(pref.preferred_genders)
  -- Возраст в диапазоне
  AND p.age BETWEEN pref.age_min AND pref.age_max
  -- Не лайкали ранее
  AND NOT EXISTS (
      SELECT 1 FROM likes l 
      WHERE l.from_user_id = :current_user_id 
        AND l.to_user_id = p.user_id
  )
  -- Геолокация (пример для PostgreSQL с postgis)
  AND ST_DWithin(
      ST_MakePoint(p.longitude, p.latitude)::geography,
      ST_MakePoint(:current_lon, :current_lat)::geography,
      pref.radius_km * 1000
  )
ORDER BY 
    p.is_verified DESC,
    p.created_at DESC
LIMIT 10;
```

### 2. Создать лайк и проверить на мэтч

```sql
-- Начало транзакции
BEGIN;

-- Создаем лайк
INSERT INTO likes (from_user_id, to_user_id, type)
VALUES (:from_user_id, :to_user_id, :like_type)
ON CONFLICT (from_user_id, to_user_id) 
DO UPDATE SET type = :like_type, created_at = NOW();

-- Проверяем взаимный лайк
SELECT COUNT(*) INTO mutual_count
FROM likes
WHERE from_user_id = :to_user_id 
  AND to_user_id = :from_user_id
  AND type IN ('like', 'superlike');

-- Если взаимно - создаем мэтч
IF mutual_count > 0 THEN
    INSERT INTO matches (user1_id, user2_id)
    VALUES (
        LEAST(:from_user_id, :to_user_id),
        GREATEST(:from_user_id, :to_user_id)
    )
    ON CONFLICT (user1_id, user2_id) DO NOTHING;
END IF;

COMMIT;
```

### 3. Получить историю сообщений для матча

```sql
SELECT 
    m.id,
    m.sender_id,
    m.text,
    m.is_read,
    m.created_at,
    u.name as sender_name,
    ph.url as sender_photo
FROM messages m
JOIN users u ON u.id = m.sender_id
LEFT JOIN photos ph ON ph.user_id = u.id AND ph.is_main = TRUE
WHERE m.match_id = :match_id
ORDER BY m.created_at ASC
LIMIT 50 OFFSET :offset;
```

### 4. Получить все активные матчи пользователя

```sql
SELECT 
    m.id,
    CASE WHEN m.user1_id = :user_id THEN m.user2_id ELSE m.user1_id END as partner_id,
    p.name as partner_name,
    p.age as partner_age,
    ph.url as partner_photo,
    m.created_at,
    -- Последнее сообщение
    (SELECT text FROM messages WHERE match_id = m.id ORDER BY created_at DESC LIMIT 1) as last_message,
    -- Количество непрочитанных
    (SELECT COUNT(*) FROM messages WHERE match_id = m.id AND sender_id != :user_id AND is_read = FALSE) as unread_count
FROM matches m
JOIN profiles p ON p.user_id = CASE WHEN m.user1_id = :user_id THEN m.user2_id ELSE m.user1_id END
LEFT JOIN photos ph ON ph.user_id = p.user_id AND ph.is_main = TRUE
WHERE (m.user1_id = :user_id OR m.user2_id = :user_id)
  AND m.is_active = TRUE
ORDER BY m.created_at DESC;
```

---

## Миграции

Структура папок для Alembic миграций:

```
backend/db/migrations/
├── versions/
│   ├── 001_create_users_table.py
│   ├── 002_create_profiles_table.py
│   ├── 003_create_preferences_table.py
│   ├── 004_create_likes_table.py
│   ├── 005_create_matches_table.py
│   ├── 006_create_messages_table.py
│   ├── 007_create_photos_table.py
│   └── 008_add_indexes.py
├── env.py
└── script.py.mako
```

---

## Seed данные (для тестирования)

```sql
-- Тестовые пользователи
INSERT INTO users (telegram_id, email, is_verified) VALUES
(1001, NULL, TRUE),
(1002, NULL, TRUE),
(1003, NULL, TRUE),
(1004, NULL, FALSE);

-- Тестовые профили
INSERT INTO profiles (user_id, name, age, bio, gender, orientation, latitude, longitude) VALUES
((SELECT id FROM users WHERE telegram_id = 1001), 'Alex', 25, 'Love hiking and coffee', 'male', 'straight', 55.7558, 37.6173),
((SELECT id FROM users WHERE telegram_id = 1002), 'Maria', 23, 'Art enthusiast', 'female', 'straight', 55.7512, 37.6156),
((SELECT id FROM users WHERE telegram_id = 1003), 'John', 30, 'Software engineer', 'male', 'bi', 55.7600, 37.6200),
((SELECT id FROM users WHERE telegram_id = 1004), 'Anna', 27, 'Travel blogger', 'female', 'straight', 55.7480, 37.6100);

-- Предпочтения
INSERT INTO preferences (user_id, preferred_genders, age_min, age_max, radius_km) VALUES
((SELECT id FROM users WHERE telegram_id = 1001), ARRAY['female']::gender_type[], 20, 30, 50),
((SELECT id FROM users WHERE telegram_id = 1002), ARRAY['male']::gender_type[], 23, 35, 100),
((SELECT id FROM users WHERE telegram_id = 1003), ARRAY['male', 'female']::gender_type[], 25, 40, 75),
((SELECT id FROM users WHERE telegram_id = 1004), ARRAY['male']::gender_type[], 25, 35, 50);
```

---

## Оптимизация и индексы

### Сводная таблица индексов

| Таблица | Индекс | Тип | Назначение |
|---------|--------|-----|------------|
| users | idx_users_telegram_id | B-tree | Поиск по Telegram ID |
| users | idx_users_email | B-tree | Поиск по email |
| profiles | idx_profiles_user_id | B-tree | Join с users |
| profiles | idx_profiles_gender_age | Composite | Matching алгоритм |
| likes | idx_likes_from_to | Unique | Проверка дубликатов |
| likes | idx_likes_mutual | Partial | Проверка взаимности |
| matches | idx_matches_user1, idx_matches_user2 | B-tree | Поиск матчей |
| messages | idx_messages_match_created | Composite | Пагинация чата |
| photos | idx_photos_sort_order | Composite | Сортировка фото |

---

## Примечания

1. **UUID вместо INTEGER**: Для безопасности и распределенности
2. **TIMESTAMPTZ**: Всегда используем timezone-aware timestamps
3. **CHECK constraints**: Валидация данных на уровне БД
4. **ON DELETE CASCADE**: Автоматическая очистка связанных данных
5. **GIST индекс**: Для гео-запросов (требует расширения postgis)
