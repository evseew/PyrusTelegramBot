-- Схема базы данных для Pyrus Telegram Bot
-- Для Supabase (PostgreSQL)

-- Зарегистрированные пользователи
CREATE TABLE users (
    user_id      INT PRIMARY KEY,         -- Pyrus user_id
    telegram_id  BIGINT NOT NULL UNIQUE,  -- Telegram chat_id
    phone        VARCHAR(20),             -- Телефон в формате E.164
    full_name    TEXT,                    -- ФИО из Pyrus
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Очередь напоминаний: одна строка на (task_id, user_id)
CREATE TABLE pending_notifications (
    task_id                   BIGINT NOT NULL,
    user_id                   INT NOT NULL,
    first_mention_at          TIMESTAMPTZ NOT NULL,
    last_mention_at           TIMESTAMPTZ NOT NULL,
    last_mention_comment_id   BIGINT,
    last_mention_comment_text TEXT,
    next_send_at              TIMESTAMPTZ NOT NULL,
    times_sent                INT DEFAULT 0,
    PRIMARY KEY (task_id, user_id)
);

-- Индексы для производительности
CREATE INDEX idx_pending_notifications_next_send_at ON pending_notifications(next_send_at);
CREATE INDEX idx_pending_notifications_user_id ON pending_notifications(user_id);

-- Идемпотентность по комментариям
CREATE TABLE processed_comments (
    task_id      BIGINT NOT NULL,
    comment_id   BIGINT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (task_id, comment_id)
);

-- Индекс для очистки старых записей
CREATE INDEX idx_processed_comments_processed_at ON processed_comments(processed_at);

-- Глобальные настройки
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Логи событий (опционально с автоочисткой)
CREATE TABLE logs (
    id      BIGSERIAL PRIMARY KEY,
    event   TEXT,            -- 'link_user','enqueue','notify_sent','notify_skip','cancel_reacted','cancel_closed'
    payload JSONB,
    ts      TIMESTAMPTZ DEFAULT now()
);

-- Индекс для очистки старых логов
CREATE INDEX idx_logs_ts ON logs(ts);

-- Начальные данные
INSERT INTO settings (key, value) VALUES 
    ('service_enabled', 'false');

-- Политики безопасности Row Level Security (для Supabase)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs ENABLE ROW LEVEL SECURITY;

-- Политика: только сервис может управлять данными (отключаем доступ через API)
-- В продакшене нужно будет настроить service_role для обхода RLS
