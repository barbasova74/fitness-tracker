
# FitTrack — система учёта тренировок

Веб-приложение для регистрации и учёта физической активности с автоматическим расчётом энергозатрат.

## Возможности

- Регистрация и авторизация по email и паролю
- Выбор вида физической активности
- Запуск, пауза и завершение тренировки
- Расчёт калорий на основе MET
- Просмотр и удаление тренировок

## Технологии

- Frontend: React, Vite
- Backend: Python, FastAPI
- Database: PostgreSQL
- Web-service: Python, FastAPI
- Контейнеризация: Docker Compose

## Архитектура

Приложение состоит из четырёх контейнеров:

1. frontend — пользовательский интерфейс
2. backend — REST API и бизнес-логика
3. db — хранение пользователей и тренировок
4. web-service — расчёт энергозатрат

## Запуск

Требуется Docker с поддержкой Docker Compose.

1. Скопировать `.env.example` в `.env`
2. Задать пароль PostgreSQL и случайный JWT_SECRET_KEY
3. Выполнить:

   docker compose up -d --build

## Адреса

- Приложение: http://localhost:3000
- Backend Swagger: http://localhost:8002/docs
- Calorie Service Swagger: http://localhost:8001/docs

## База данных

PostgreSQL содержит три таблицы:
users, activity_types, workouts.

При первой инициализации выполняется db/init.sql.

## Расчёт калорий

Используется формула MET:

Ккал = MET × 3.5 × вес (кг) / 200 × время (мин)

Результат является приблизительной оценкой расхода энергии.
