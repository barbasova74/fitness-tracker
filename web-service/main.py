
from fastapi import FastAPI
from pydantic import BaseModel, Field

# Создаём приложение FastAPI
app = FastAPI(title="FitTrack Calorie Service")


# Данные, которые принимает сервис
class CalorieRequest(BaseModel):
    met: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    duration_seconds: int = Field(gt=0)


# Расчёт потраченных калорий
@app.post("/calculate")
def calculate_calories(data: CalorieRequest):
    duration_minutes = data.duration_seconds / 60

    calories = (
        data.met * 3.5 * data.weight_kg
        / 200 * duration_minutes
    )

    return {
        "calories_burned": round(calories, 2)
    }


# Проверка работы сервиса
@app.get("/health")
def health():
    return {"status": "ok"}
