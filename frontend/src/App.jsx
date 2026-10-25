
import { useEffect, useState } from "react";
import {
  Activity, Plus, Trash2, Play, Pause,
  Square, LogOut, ArrowLeft
} from "lucide-react";

const API = "/api";

async function request(path, options = {}, token = "") {
  const response = await fetch(API + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
      ...options.headers
    }
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Ошибка ${response.status}`
    );
  }

  return data;
}

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;

  return [h, m, s]
    .map(n => String(n).padStart(2, "0"))
    .join(":");
}

export default function App() {
  const [token, setToken] = useState(
    () => sessionStorage.getItem("fittrack_token") || ""
  );
  const [page, setPage] = useState("list");
  const [registerMode, setRegisterMode] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [weight, setWeight] = useState("");
  const [activities, setActivities] = useState([]);
  const [workouts, setWorkouts] = useState([]);
  const [activityId, setActivityId] = useState("");
  const [activeWorkout, setActiveWorkout] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;

    async function load() {
      try {
        const [types, history] = await Promise.all([
          request("/activities", {}, token),
          request("/workouts", {}, token)
        ]);

        setActivities(types);
        setActivityId(
          current => current || String(types[0]?.id || "")
        );
        setWorkouts(history);
      } catch (err) {
        setError(err.message);
      }
    }

    load();
  }, [token]);

  useEffect(() => {
    if (!activeWorkout || activeWorkout.paused) return;

    const update = () => {
      setElapsed(
        activeWorkout.baseSeconds +
        Math.floor(
          (Date.now() - activeWorkout.resumedAt) / 1000
        )
      );
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [activeWorkout]);

  async function run(action) {
    setBusy(true);
    setError("");

    try {
      return await action();
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function submitAuth(event) {
    event.preventDefault();

    await run(async () => {
      if (registerMode) {
        await request("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            weight_kg: Number(weight)
          })
        });
      }

      const result = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });

      sessionStorage.setItem(
        "fittrack_token",
        result.access_token
      );
      setToken(result.access_token);
      setPassword("");
      setPage("list");
    });
  }

  function logout() {
    sessionStorage.removeItem("fittrack_token");
    setToken("");
    setWorkouts([]);
    setActiveWorkout(null);
    setPage("list");
    setError("");
  }

  async function refreshWorkouts() {
    const data = await request("/workouts", {}, token);
    setWorkouts(data);
  }

  async function startWorkout() {
    await run(async () => {
      const result = await request("/workouts/start", {
        method: "POST",
        body: JSON.stringify({
          activity_type_id: Number(activityId)
        })
      }, token);

      setElapsed(0);
      setActiveWorkout({
        id: result.id,
        baseSeconds: 0,
        resumedAt: Date.now(),
        paused: false
      });
    });
  }

  async function pauseWorkout() {
    await run(async () => {
      const result = await request(
        `/workouts/${activeWorkout.id}/pause`,
        { method: "POST" },
        token
      );

      setElapsed(result.duration_seconds);
      setActiveWorkout({
        ...activeWorkout,
        baseSeconds: result.duration_seconds,
        resumedAt: null,
        paused: true
      });
    });
  }

  async function resumeWorkout() {
    await run(async () => {
      await request(
        `/workouts/${activeWorkout.id}/resume`,
        { method: "POST" },
        token
      );

      setActiveWorkout({
        ...activeWorkout,
        resumedAt: Date.now(),
        paused: false
      });
    });
  }

  async function finishWorkout() {
    await run(async () => {
      const result = await request(
        `/workouts/${activeWorkout.id}/finish`,
        { method: "POST" },
        token
      );

      setActiveWorkout(null);
      setElapsed(0);
      await refreshWorkouts();
      setPage("list");
      alert(
        `Тренировка завершена!\n` +
        `Время: ${formatTime(result.duration_seconds)}\n` +
        `Калории: ${result.calories_burned} ккал`
      );
    });
  }

  async function deleteWorkout(id) {
    if (!window.confirm("Удалить эту тренировку?")) {
      return;
    }

    await run(async () => {
      await request(
        `/workouts/${id}`,
        { method: "DELETE" },
        token
      );

      await refreshWorkouts();
    });
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="brand">
            <Activity size={27} />
            FitTrack
          </div>

          <h1>
            {registerMode ? "Регистрация" : "С возвращением!"}
          </h1>
          <p className="muted">
            {registerMode
              ? "Создай аккаунт для учёта тренировок"
              : "Войди, чтобы продолжить тренировки"}
          </p>

          <form onSubmit={submitAuth}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
            />

            <label>Пароль</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              minLength={registerMode ? 8 : undefined}
              required
            />

            {registerMode && (
              <>
                <label>Вес (кг)</label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  step="0.1"
                  value={weight}
                  onChange={e => setWeight(e.target.value)}
                  required
                />
              </>
            )}

            {error && <p className="error">{error}</p>}

            <button
              className="primary full"
              disabled={busy}
              type="submit"
            >
              {registerMode ? "Зарегистрироваться" : "Войти"}
            </button>
          </form>

          <button
            className="text-button"
            onClick={() => {
              setRegisterMode(!registerMode);
              setError("");
            }}
          >
            {registerMode
              ? "Уже есть аккаунт? Войти"
              : "Нет аккаунта? Зарегистрироваться"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <div className="brand">
          <Activity size={26} />
          FitTrack
        </div>

        <button className="logout" onClick={logout}>
          <LogOut size={18} />
          Выйти
        </button>
      </header>

      <main>
        {error && (
          <div className="error-box">{error}</div>
        )}

        {page === "list" ? (
          <>
            <div className="page-heading">
              <div>
                <h1>Мои тренировки</h1>
                <p className="muted">
                  История выполненных тренировок
                </p>
              </div>

              <button
                className="primary"
                onClick={() => {
                  setError("");
                  setPage("new");
                }}
              >
                <Plus size={18} />
                Добавить тренировку
              </button>
            </div>

            {workouts.length === 0 ? (
              <div className="empty">
                <Activity size={42} />
                <h2>Тренировок пока нет</h2>
                <p>Начни первую тренировку!</p>
              </div>
            ) : (
              <div className="workout-list">
                {workouts.map(workout => (
                  <div className="workout" key={workout.id}>
                    <div className="workout-icon">
                      <Activity size={23} />
                    </div>

                    <div className="workout-info">
                      <strong>{workout.activity_name}</strong>
                      <span className="muted">
                        {new Date(
                          workout.started_at
                        ).toLocaleDateString("ru-RU")}
                      </span>
                    </div>

                    <div className="workout-values">
                      <span>
                        {formatTime(workout.duration_seconds)}
                      </span>
                      <strong>
                        {workout.calories_burned} ккал
                      </strong>
                    </div>

                    <button
                      className="delete"
                      disabled={busy}
                      onClick={() => deleteWorkout(workout.id)}
                      title="Удалить тренировку"
                    >
                      <Trash2 size={19} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="training-page">
            <button
              className="back"
              disabled={!!activeWorkout}
              onClick={() => setPage("list")}
            >
              <ArrowLeft size={18} />
              Мои тренировки
            </button>

            <div className="training-card">
              <h1>Новая тренировка</h1>

              <label>Вид активности</label>
              <select
                value={activityId}
                disabled={!!activeWorkout}
                onChange={e => setActivityId(e.target.value)}
              >
                {activities.map(activity => (
                  <option
                    key={activity.id}
                    value={activity.id}
                  >
                    {activity.name}
                  </option>
                ))}
              </select>

              <div className="timer">
                {formatTime(elapsed)}
              </div>

              <p className="timer-status">
                {!activeWorkout
                  ? "Готова к тренировке"
                  : activeWorkout.paused
                    ? "На паузе"
                    : "Тренировка идёт"}
              </p>

              <div className="actions">
                {!activeWorkout ? (
                  <button
                    className="primary full"
                    disabled={busy || !activityId}
                    onClick={startWorkout}
                  >
                    <Play size={19} />
                    Начать тренировку
                  </button>
                ) : (
                  <>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={
                        activeWorkout.paused
                          ? resumeWorkout
                          : pauseWorkout
                      }
                    >
                      {activeWorkout.paused
                        ? <Play size={19} />
                        : <Pause size={19} />}
                      {activeWorkout.paused
                        ? "Продолжить"
                        : "Пауза"}
                    </button>

                    <button
                      className="danger"
                      disabled={busy}
                      onClick={finishWorkout}
                    >
                      <Square size={17} />
                      Завершить
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
