
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from psycopg.errors import UniqueViolation
from workouts import router as workouts_router

from database import get_connection
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_id
)

app = FastAPI(
    title="FitTrack — API системы учёта тренировок",
    description="Регистрация пользователей и управление физической активностью",
    version="1.0.0"
)

app.include_router(workouts_router)

# Модели входных данных
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    weight_kg: float = Field(gt=0, le=500)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Проверка сервера
@app.get(
    "/health",
    tags=["Система"],
    summary="Проверка состояния сервера"
)
def health():
    return {"status": "ok"}


# Справочник активностей
@app.get(
    "/activities",
    tags=["Активности"],
    summary="Получить список активностей"
)
def get_activities():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, met_value
                FROM activity_types
                ORDER BY id
            """)
            return cursor.fetchall()


# Регистрация
@app.post(
    "/auth/register",
    tags=["Авторизация"],
    summary="Регистрация нового пользователя",
    status_code=201
)
def register(data: RegisterRequest):
    email = str(data.email).strip().lower()
    password_hash = hash_password(data.password)

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users
                        (email, password_hash, weight_kg)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, weight_kg
                """, (
                    email,
                    password_hash,
                    data.weight_kg
                ))

                user = cursor.fetchone()

        return user

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Пользователь с таким email уже существует"
        )


# Вход
@app.post(
    "/auth/login",
    tags=["Авторизация"],
    summary="Вход по email и паролю"
)
def login(data: LoginRequest):
    email = str(data.email).strip().lower()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, password_hash
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()

    if not user or not verify_password(
        data.password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль"
        )

    access_token = create_access_token(user["id"])

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# Профиль авторизованного пользователя
@app.get(
    "/auth/me",
    tags=["Авторизация"],
    summary="Получить данные своего профиля"
)
def get_profile(
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, weight_kg, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Пользователь не найден"
        )

    return user
