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

### AI helpers

Set `GEMINI_API_KEY` (and `OPENROUTER_API_KEY` for the Qwen / Nemotron fallbacks). Models are tried in the order of `LLM_MODELS`.

- `POST /elders/{id}/prescriptions/scan`: reads a prescription photo into draft medicines. **Nothing is saved** until the caregiver checks them and calls `POST /elders/{id}/prescriptions/confirm`.
- `POST /elders/{id}/documents` and `POST /elders/{id}/ask`: answers questions only from that elder's documents (stored in ChromaDB in `CHROMA_DIR`), with numbered sources. Dosage questions are refused.
- `GET /elders/{id}/summary/weekly`: last 7 days taken/missed per medicine, plus a short AI summary.

The first time documents are added, ChromaDB downloads its small local embedding model. Tests never call a real AI service.

No database migrations yet: after pulling new model changes, delete `elderly_care.db` so tables are recreated.

## App (PWA)

React + Vite app in `frontend/`. Run the backend first, then:

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 (calls the backend through /api)
npm test
npm run build   # production build in dist/
```

- **Caregivers** open the app, log in, add elders, medicines, schedules and appointments.
- **Elders** use the "Elder screen link" from the caregiver page (`/#/screen/<token>`): one big screen with the tablet photo, name, dose, food timing, a huge **I TOOK IT** button, **Remind me later** and **SOS**. Reminders are spoken in Kannada, Hindi or English. If the phone has no voice for the elder's language, the reminder is spoken in English. Medicine and elder names typed in Kannada or Hindi script sound best.
