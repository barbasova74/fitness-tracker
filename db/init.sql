
-- 1. Пользователи
CREATE TABLE users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    weight_kg NUMERIC(5,2) NOT NULL
        CHECK (weight_kg > 0),
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

-- 2. Справочник активностей
CREATE TABLE activity_types (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    met_value NUMERIC(5,2) NOT NULL
        CHECK (met_value > 0)
);

-- 3. Тренировки
CREATE TABLE workouts (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id INTEGER NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,

    activity_type_id INTEGER NOT NULL
        REFERENCES activity_types(id),

    duration_seconds INTEGER NOT NULL DEFAULT 0
        CHECK (duration_seconds >= 0),

    calories_burned NUMERIC(8,2)
        CHECK (calories_burned >= 0),

    weight_kg NUMERIC(5,2) NOT NULL
        CHECK (weight_kg > 0),

    status VARCHAR(20) NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'paused', 'completed')),

    started_at TIMESTAMPTZ NOT NULL,
    last_resumed_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_workout_status CHECK (
        (status = 'in_progress'
            AND last_resumed_at IS NOT NULL
            AND finished_at IS NULL)
        OR
        (status = 'paused'
            AND last_resumed_at IS NULL
            AND finished_at IS NULL)
        OR
        (status = 'completed'
            AND last_resumed_at IS NULL
            AND finished_at IS NOT NULL)
    )
);

-- Индекс для быстрого получения тренировок пользователя
CREATE INDEX idx_workouts_user
    ON workouts(user_id, started_at DESC);

-- Тестовые виды активности
INSERT INTO activity_types (name, met_value)
VALUES
    ('Хатха-йога', 2.50),
    ('Ходьба', 3.50),
    ('Силовая тренировка', 3.50),
    ('Интенсивная силовая', 6.00),
    ('Велосипед', 6.80),
    ('Бег (8 км/ч)', 8.30),
    ('Бег (10 км/ч)', 9.80);
