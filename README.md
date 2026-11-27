# Elderly Care & Medicine Reminder

## Backend

FastAPI + SQLAlchemy API in `backend/`. Uses SQLite by default; set `DATABASE_URL` (see `backend/.env.example`) for MySQL, e.g. `mysql+pymysql://user:pass@host:3306/elderly_care`.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload   # API docs at http://127.0.0.1:8000/docs
pytest                          # run tests
ruff check . && ruff format --check .
```

### Reminders and alerts

While the server runs, a background job creates each elder's doses for today (every 30 min) and marks doses **missed** 30 minutes after they're due (or after a snooze ends).
Caregivers get a Telegram message for missed doses and when a medicine's stock reaches its refill threshold.

1. Create a bot with [@BotFather](https://t.me/BotFather) and put its token in `TELEGRAM_BOT_TOKEN`.
2. Each caregiver messages the bot, then saves their chat id with `PUT /auth/me/telegram`.

### Elder screen, SOS and appointments

Each elder has a `screen_token` (shown in `GET /elders/{id}`). The elder's device sends it as the `X-Screen-Token` header to `GET /screen` (next dose and next appointment), `POST /screen/doses/{id}/take`, `POST /screen/doses/{id}/snooze` and `POST /screen/sos`. SOS sends a Telegram alert to every caregiver. If a phone is lost, `POST /elders/{id}/screen-token` makes a new token.

No database migrations yet: after pulling new model changes, delete `elderly_care.db` so tables are recreated.
