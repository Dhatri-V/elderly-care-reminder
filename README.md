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
