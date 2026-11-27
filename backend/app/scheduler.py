from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal
from app.services import generate_today_for_all, mark_missed


def run(job) -> None:
    db = SessionLocal()
    try:
        job(db)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    # Generation is idempotent, so running it often just picks up new schedules and new days.
    scheduler.add_job(
        run, "interval", minutes=30, args=[generate_today_for_all], next_run_time=datetime.now(UTC)
    )
    scheduler.add_job(run, "interval", minutes=1, args=[mark_missed])
    scheduler.start()
    return scheduler
