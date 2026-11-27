from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import DoseEvent, Elder, Medicine, Schedule
from app.pattern import parse_pattern


def generate_doses(db: Session, elder: Elder, day: date) -> int:
    """Create the day's DoseEvents from active schedules. Safe to run more than once.

    Returns how many new doses were created.
    """
    schedules = (
        db.query(Schedule)
        .join(Medicine)
        .filter(Medicine.elder_id == elder.id, Schedule.start_date <= day)
        .filter((Schedule.end_date.is_(None)) | (Schedule.end_date >= day))
        .all()
    )
    tz = ZoneInfo(elder.timezone)
    created = 0
    for s in schedules:
        doses = parse_pattern(s.pattern)
        times = (s.morning_time, s.afternoon_time, s.night_time)
        for quantity, slot_time in zip(doses, times, strict=True):
            if quantity == 0:
                continue
            local = datetime.combine(day, slot_time, tzinfo=tz)
            scheduled_at = local.astimezone(UTC).replace(tzinfo=None)
            exists = db.query(DoseEvent).filter_by(schedule_id=s.id, scheduled_at=scheduled_at)
            if exists.first():
                continue
            db.add(
                DoseEvent(
                    elder_id=elder.id,
                    medicine_id=s.medicine_id,
                    schedule_id=s.id,
                    scheduled_at=scheduled_at,
                    quantity=quantity,
                )
            )
            created += 1
    db.commit()
    return created


def next_dose(db: Session, elder: Elder) -> DoseEvent | None:
    """Earliest dose that is pending, or snoozed with the snooze time passed."""
    now = utcnow()
    return (
        db.query(DoseEvent)
        .filter(DoseEvent.elder_id == elder.id)
        .filter(
            (DoseEvent.status == "pending")
            | ((DoseEvent.status == "snoozed") & (DoseEvent.snooze_until <= now))
        )
        .order_by(DoseEvent.scheduled_at)
        .first()
    )


def take_dose(db: Session, dose: DoseEvent) -> None:
    dose.status = "taken"
    dose.taken_at = utcnow()
    dose.medicine.stock_count = max(0, dose.medicine.stock_count - dose.quantity)
    db.commit()


def snooze_dose(db: Session, dose: DoseEvent, minutes: int = 10) -> None:
    dose.status = "snoozed"
    dose.snooze_until = utcnow() + timedelta(minutes=minutes)
    db.commit()
