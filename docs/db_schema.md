# Схема базы данных

## Таблицы

### users
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

### profiles
```sql
CREATE TABLE profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    age             INTEGER NOT NULL CHECK (age >= 18),
    bio             TEXT,
    gender          VARCHAR(20) NOT NULL,
    latitude        DECIMAL(10, 8),
    longitude       DECIMAL(11, 8),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_gender_age ON profiles(gender, age);
```

---

### preferences
```sql
CREATE TABLE preferences (
    user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_gender VARCHAR(20) NOT NULL,
    age_min         INTEGER DEFAULT 18,
    age_max         INTEGER DEFAULT 50,
    radius_km       INTEGER DEFAULT 100
);
```

---

### likes
```sql
CREATE TABLE likes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_like         BOOLEAN NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (from_user_id, to_user_id)
);

CREATE INDEX idx_likes_from ON likes(from_user_id);
CREATE INDEX idx_likes_to ON likes(to_user_id);
```

---

### matches
```sql
CREATE TABLE matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CHECK (user1_id < user2_id)
);

CREATE INDEX idx_matches_user1 ON matches(user1_id);
CREATE INDEX idx_matches_user2 ON matches(user2_id);
```

---

### messages
```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID REFERENCES matches(id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_match ON messages(match_id, created_at);
```

---

### photos
```sql
CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    url             VARCHAR(500) NOT NULL,
    is_main         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photos_user ON photos(user_id);
```

---

## Связи

```
users (1) ── (1) profiles
  │
  │ (1) ── (1) preferences
  │
  │ (1) ── (N) likes (from_user)
  │
  │ (1) ── (N) likes (to_user)
  │
  │ (1) ── (N) matches (user1)
  │
  │ (1) ── (N) matches (user2)
  │
  │ (1) ── (N) messages
  │
  │ (1) ── (N) photos
```
