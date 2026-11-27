from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import check_access, current_user
from app.models import Appointment, User
from app.schemas import AppointmentIn, AppointmentOut

router = APIRouter(tags=["appointments"])


def get_appointment(db: Session, user: User, appointment_id: int) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    check_access(db, user, appointment.elder_id)
    return appointment


@router.post("/elders/{elder_id}/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(
    elder_id: int,
    body: AppointmentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    check_access(db, user, elder_id)
    appointment = Appointment(elder_id=elder_id, **body.model_dump())
    db.add(appointment)
    db.commit()
    return appointment


@router.get("/elders/{elder_id}/appointments", response_model=list[AppointmentOut])
def list_appointments(
    elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    check_access(db, user, elder_id)
    return db.query(Appointment).filter_by(elder_id=elder_id).order_by(Appointment.starts_at).all()


@router.put("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: int,
    body: AppointmentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    appointment = get_appointment(db, user, appointment_id)
    for key, value in body.model_dump().items():
        setattr(appointment, key, value)
    db.commit()
    return appointment


@router.delete("/appointments/{appointment_id}", status_code=204)
def delete_appointment(
    appointment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(get_appointment(db, user, appointment_id))
    db.commit()
