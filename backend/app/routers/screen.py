"""Endpoints for the elder's device. It sends the elder's screen token, not a login."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Appointment, DoseEvent, Elder
from app.notify import alert_caregivers
from app.schemas import DoseOut, NextDose, Screen
from app.services import next_dose, snooze_dose, take_dose

router = APIRouter(prefix="/screen", tags=["elder screen"])


def screen_elder(x_screen_token: str = Header(), db: Session = Depends(get_db)) -> Elder:
    elder = db.query(Elder).filter_by(screen_token=x_screen_token).first()
    if elder is None:
        raise HTTPException(401, "Invalid screen link")
    return elder


def elder_dose(db: Session, elder: Elder, dose_id: int) -> DoseEvent:
    dose = db.get(DoseEvent, dose_id)
    if dose is None or dose.elder_id != elder.id:
        raise HTTPException(404, "Dose not found")
    if dose.status == "taken":
        raise HTTPException(409, "Dose already taken")
    return dose


@router.get("", response_model=Screen)
def get_screen(elder: Elder = Depends(screen_elder), db: Session = Depends(get_db)):
    dose = next_dose(db, elder)
    now_local = datetime.now(ZoneInfo(elder.timezone)).replace(tzinfo=None)
    appointment = (
        db.query(Appointment)
        .filter(Appointment.elder_id == elder.id, Appointment.starts_at >= now_local)
        .order_by(Appointment.starts_at)
        .first()
    )
    return Screen(
        elder_name=elder.name,
        language=elder.language,
        next_dose=NextDose.from_dose(dose) if dose else None,
        next_appointment=appointment,
    )


@router.post("/doses/{dose_id}/take", response_model=DoseOut)
def take(dose_id: int, elder: Elder = Depends(screen_elder), db: Session = Depends(get_db)):
    dose = elder_dose(db, elder, dose_id)
    take_dose(db, dose)
    return dose


@router.post("/doses/{dose_id}/snooze", response_model=DoseOut)
def snooze(
    dose_id: int,
    minutes: int = 10,
    elder: Elder = Depends(screen_elder),
    db: Session = Depends(get_db),
):
    dose = elder_dose(db, elder, dose_id)
    snooze_dose(db, dose, minutes)
    return dose


@router.post("/sos")
def sos(elder: Elder = Depends(screen_elder), db: Session = Depends(get_db)):
    alert_caregivers(db, elder.id, f"SOS! {elder.name} pressed the emergency button.")
    return {"ok": True}
