from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.pattern import parse_pattern

Language = Literal["kn", "hi", "en"]
FoodTiming = Literal["before", "after", "with", "any"]


class Login(BaseModel):
    email: str = Field(pattern=r"^\S+@\S+\.\S+$")
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class TelegramIn(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ElderIn(BaseModel):
    name: str = Field(min_length=1)
    language: Language = "en"
    timezone: str = "Asia/Kolkata"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError(f"unknown timezone: {v}") from None
        return v


class ElderOut(ElderIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class MedicineIn(BaseModel):
    name: str = Field(min_length=1)
    strength: str | None = None
    photo_url: str | None = None
    food_timing: FoodTiming = "any"
    stock_count: float = Field(0, ge=0)
    refill_threshold: float = Field(0, ge=0)


class MedicineOut(MedicineIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    elder_id: int


class ScheduleIn(BaseModel):
    pattern: str
    morning_time: time = time(8, 0)
    afternoon_time: time = time(13, 0)
    night_time: time = time(20, 0)
    start_date: date
    end_date: date | None = None

    @field_validator("pattern")
    @classmethod
    def valid_pattern(cls, v: str) -> str:
        parse_pattern(v)  # raises ValueError -> 422
        return v


class ScheduleOut(ScheduleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    medicine_id: int


class DoseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    elder_id: int
    medicine_id: int
    scheduled_at: datetime
    quantity: float
    status: str
    taken_at: datetime | None
    snooze_until: datetime | None


class NextDose(BaseModel):
    dose_id: int
    medicine_name: str
    strength: str | None
    photo_url: str | None
    quantity: float
    food_timing: str
    scheduled_at: datetime
