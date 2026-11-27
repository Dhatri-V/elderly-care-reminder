from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import check_access, current_user
from app.models import DoseEvent, User
from app.schemas import DoseOut, NextDose
from app.services import generate_doses, next_dose, snooze_dose, take_dose

router = APIRouter(tags=["doses"])


def get_dose(db: Session, user: User, dose_id: int) -> DoseEvent:
    dose = db.get(DoseEvent, dose_id)
    if dose is None:
        raise HTTPException(404, "Dose not found")
    check_access(db, user, dose.elder_id)
    return dose


@router.post("/elders/{elder_id}/doses/generate")
def generate(
    elder_id: int, day: date, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    elder = check_access(db, user, elder_id)
    return {"created": generate_doses(db, elder, day)}


@router.get("/elders/{elder_id}/doses", response_model=list[DoseOut])
def list_doses(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    check_access(db, user, elder_id)
    return db.query(DoseEvent).filter_by(elder_id=elder_id).order_by(DoseEvent.scheduled_at).all()


@router.get("/elders/{elder_id}/next-dose", response_model=NextDose | None)
def get_next_dose(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    dose = next_dose(db, check_access(db, user, elder_id))
    if dose is None:
        return None
    return NextDose(
        dose_id=dose.id,
        medicine_name=dose.medicine.name,
        strength=dose.medicine.strength,
        photo_url=dose.medicine.photo_url,
        quantity=dose.quantity,
        food_timing=dose.medicine.food_timing,
        scheduled_at=dose.scheduled_at,
    )


@router.post("/doses/{dose_id}/take", response_model=DoseOut)
def take(dose_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    dose = get_dose(db, user, dose_id)
    if dose.status == "taken":
        raise HTTPException(409, "Dose already taken")
    take_dose(db, dose)
    return dose


@router.post("/doses/{dose_id}/snooze", response_model=DoseOut)
def snooze(
    dose_id: int,
    minutes: int = 10,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    dose = get_dose(db, user, dose_id)
    if dose.status == "taken":
        raise HTTPException(409, "Dose already taken")
    snooze_dose(db, dose, minutes)
    return dose
