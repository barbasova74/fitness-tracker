
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from database import get_connection

router = APIRouter(
    prefix="/workouts",
    tags=["Тренировки"]
)

CALORIE_SERVICE_URL = os.getenv(
    "CALORIE_SERVICE_URL",
    "http://web-service:8000"
)


class StartWorkoutRequest(BaseModel):
    activity_type_id: int


def get_workout(cursor, workout_id, user_id):
    cursor.execute("""
        SELECT *
        FROM workouts
        WHERE id = %s AND user_id = %s
        FOR UPDATE
    """, (workout_id, user_id))

    workout = cursor.fetchone()

    if not workout:
        raise HTTPException(
            status_code=404,
            detail="Тренировка не найдена"
        )

    return workout


def calculate_duration(workout, now):
    seconds = workout["duration_seconds"]

    if workout["status"] == "in_progress":
        difference = (
            now - workout["last_resumed_at"]
        ).total_seconds()

        seconds += max(0, int(difference))

    return seconds


# Получить историю тренировок
@router.get(
    "",
    summary="Получить список своих тренировок"
)
def list_workouts(
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    w.id,
                    a.name AS activity_name,
                    w.started_at,
                    w.finished_at,
                    w.duration_seconds,
                    w.calories_burned
                FROM workouts w
                JOIN activity_types a
                    ON a.id = w.activity_type_id
                WHERE w.user_id = %s
                  AND w.status = 'completed'
                ORDER BY w.started_at DESC
            """, (user_id,))

            return cursor.fetchall()


# Запуск тренировки
@router.post(
    "/start",
    status_code=201,
    summary="Начать новую тренировку"
)
def start_workout(
    data: StartWorkoutRequest,
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT weight_kg
                FROM users
                WHERE id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="Пользователь не найден"
                )

            cursor.execute("""
                SELECT id
                FROM activity_types
                WHERE id = %s
            """, (data.activity_type_id,))

            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Вид активности не найден"
                )

            cursor.execute("""
                INSERT INTO workouts (
                    user_id,
                    activity_type_id,
                    weight_kg,
                    started_at,
                    last_resumed_at,
                    status
                )
                VALUES (
                    %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    'in_progress'
                )
                RETURNING id, status, started_at
            """, (
                user_id,
                data.activity_type_id,
                user["weight_kg"]
            ))

            return cursor.fetchone()


# Пауза
@router.post(
    "/{workout_id}/pause",
    summary="Приостановить тренировку"
)
def pause_workout(
    workout_id: int,
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            workout = get_workout(
                cursor, workout_id, user_id
            )

            if workout["status"] != "in_progress":
                raise HTTPException(
                    status_code=409,
                    detail="Тренировка не выполняется"
                )

            now = datetime.now(timezone.utc)
            duration = calculate_duration(workout, now)

            cursor.execute("""
                UPDATE workouts
                SET status = 'paused',
                    duration_seconds = %s,
                    last_resumed_at = NULL
                WHERE id = %s
            """, (duration, workout_id))

            return {
                "id": workout_id,
                "status": "paused",
                "duration_seconds": duration
            }


# Продолжение
@router.post(
    "/{workout_id}/resume",
    summary="Продолжить тренировку"
)
def resume_workout(
    workout_id: int,
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            workout = get_workout(
                cursor, workout_id, user_id
            )

            if workout["status"] != "paused":
                raise HTTPException(
                    status_code=409,
                    detail="Тренировка не на паузе"
                )

            cursor.execute("""
                UPDATE workouts
                SET status = 'in_progress',
                    last_resumed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (workout_id,))

            return {
                "id": workout_id,
                "status": "in_progress"
            }


# Завершение с расчётом калорий
@router.post(
    "/{workout_id}/finish",
    summary="Завершить тренировку и рассчитать калории"
)
def finish_workout(
    workout_id: int,
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            workout = get_workout(
                cursor, workout_id, user_id
            )

            if workout["status"] == "completed":
                raise HTTPException(
                    status_code=409,
                    detail="Тренировка уже завершена"
                )

            now = datetime.now(timezone.utc)
            duration = calculate_duration(workout, now)

            cursor.execute("""
                SELECT met_value
                FROM activity_types
                WHERE id = %s
            """, (workout["activity_type_id"],))

            activity = cursor.fetchone()

            if not activity:
                raise HTTPException(
                    status_code=404,
                    detail="Вид активности не найден"
                )

            # Нулевая длительность — нулевой расход
            if duration == 0:
                calories = 0.0
            else:
                try:
                    response = httpx.post(
                        f"{CALORIE_SERVICE_URL}/calculate",
                        json={
                            "met": float(
                                activity["met_value"]
                            ),
                            "weight_kg": float(
                                workout["weight_kg"]
                            ),
                            "duration_seconds": duration
                        },
                        timeout=10.0
                    )

                    response.raise_for_status()
                    calories = response.json()[
                        "calories_burned"
                    ]

                except (
                    httpx.HTTPError,
                    ValueError,
                    KeyError
                ):
                    raise HTTPException(
                        status_code=502,
                        detail="Ошибка сервиса расчёта калорий"
                    )

            cursor.execute("""
                UPDATE workouts
                SET status = 'completed',
                    duration_seconds = %s,
                    calories_burned = %s,
                    last_resumed_at = NULL,
                    finished_at = %s
                WHERE id = %s
            """, (
                duration,
                calories,
                now,
                workout_id
            ))

            return {
                "id": workout_id,
                "status": "completed",
                "duration_seconds": duration,
                "calories_burned": calories
            }


# Удаление
@router.delete(
    "/{workout_id}",
    summary="Удалить тренировку"
)
def delete_workout(
    workout_id: int,
    user_id: int = Depends(get_current_user_id)
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM workouts
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (workout_id, user_id))

            deleted = cursor.fetchone()

            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail="Тренировка не найдена"
                )

    return {"message": "Тренировка удалена"}
