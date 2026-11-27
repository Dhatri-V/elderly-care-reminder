import secrets
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow


class User(Base):
    """A caregiver account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Elder(Base):
    __tablename__ = "elders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(2), default="en")  # kn / hi / en
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    # Lets the elder's device show their screen without a login.
    screen_token: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: secrets.token_urlsafe(24)
    )

    medicines: Mapped[list["Medicine"]] = relationship(cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(cascade="all, delete-orphan")


class CaregiverElder(Base):
    """Links caregivers to elders. One caregiver can manage many elders."""

    __tablename__ = "caregiver_elders"
    __table_args__ = (UniqueConstraint("user_id", "elder_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    elder_id: Mapped[int] = mapped_column(ForeignKey("elders.id", ondelete="CASCADE"))


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("elders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    strength: Mapped[str | None] = mapped_column(String(64))
    photo_url: Mapped[str | None] = mapped_column(String(1024))
    food_timing: Mapped[str] = mapped_column(String(10), default="any")  # before/after/with/any
    stock_count: Mapped[float] = mapped_column(Float, default=0)
    refill_threshold: Mapped[float] = mapped_column(Float, default=0)
    refill_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="medicine", cascade="all, delete-orphan"
    )


class Schedule(Base):
    """Dose pattern like 1-0-1 (morning-afternoon-night) with a time for each slot."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id", ondelete="CASCADE"))
    pattern: Mapped[str] = mapped_column(String(32))
    morning_time: Mapped[time] = mapped_column(Time, default=time(8, 0))
    afternoon_time: Mapped[time] = mapped_column(Time, default=time(13, 0))
    night_time: Mapped[time] = mapped_column(Time, default=time(20, 0))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    medicine: Mapped[Medicine] = relationship(back_populates="schedules")
    doses: Mapped[list["DoseEvent"]] = relationship(cascade="all, delete-orphan")


class DoseEvent(Base):
    __tablename__ = "dose_events"
    # Makes daily generation idempotent: one event per schedule per time.
    __table_args__ = (UniqueConstraint("schedule_id", "scheduled_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("elders.id", ondelete="CASCADE"))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id", ondelete="CASCADE"))
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    quantity: Mapped[float] = mapped_column(Float)
    # pending / taken / snoozed / missed
    status: Mapped[str] = mapped_column(String(10), default="pending")
    taken_at: Mapped[datetime | None] = mapped_column(DateTime)
    snooze_until: Mapped[datetime | None] = mapped_column(DateTime)

    medicine: Mapped[Medicine] = relationship()
    elder: Mapped[Elder] = relationship()


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    elder_id: Mapped[int] = mapped_column(ForeignKey("elders.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    doctor: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime)  # elder's local time
