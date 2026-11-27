from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import check_access, current_user
from app.models import Medicine, Schedule, User
from app.schemas import MedicineIn, MedicineOut, ScheduleIn, ScheduleOut

router = APIRouter(tags=["medicines"])


def get_medicine(db: Session, user: User, medicine_id: int) -> Medicine:
    medicine = db.get(Medicine, medicine_id)
    if medicine is None:
        raise HTTPException(404, "Medicine not found")
    check_access(db, user, medicine.elder_id)
    return medicine


def get_schedule(db: Session, user: User, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(404, "Schedule not found")
    check_access(db, user, schedule.medicine.elder_id)
    return schedule


# Medicines


@router.post("/elders/{elder_id}/medicines", response_model=MedicineOut, status_code=201)
def create_medicine(
    elder_id: int,
    body: MedicineIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    check_access(db, user, elder_id)
    medicine = Medicine(elder_id=elder_id, **body.model_dump())
    db.add(medicine)
    db.commit()
    return medicine


@router.get("/elders/{elder_id}/medicines", response_model=list[MedicineOut])
def list_medicines(
    elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return check_access(db, user, elder_id).medicines


@router.get("/medicines/{medicine_id}", response_model=MedicineOut)
def read_medicine(
    medicine_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return get_medicine(db, user, medicine_id)


@router.put("/medicines/{medicine_id}", response_model=MedicineOut)
def update_medicine(
    medicine_id: int,
    body: MedicineIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    medicine = get_medicine(db, user, medicine_id)
    for key, value in body.model_dump().items():
        setattr(medicine, key, value)
    db.commit()
    return medicine


@router.delete("/medicines/{medicine_id}", status_code=204)
def delete_medicine(
    medicine_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(get_medicine(db, user, medicine_id))
    db.commit()


# Schedules


@router.post("/medicines/{medicine_id}/schedules", response_model=ScheduleOut, status_code=201)
def create_schedule(
    medicine_id: int,
    body: ScheduleIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    get_medicine(db, user, medicine_id)
    schedule = Schedule(medicine_id=medicine_id, **body.model_dump())
    db.add(schedule)
    db.commit()
    return schedule


@router.get("/medicines/{medicine_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(
    medicine_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return get_medicine(db, user, medicine_id).schedules


@router.put("/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    body: ScheduleIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    schedule = get_schedule(db, user, schedule_id)
    for key, value in body.model_dump().items():
        setattr(schedule, key, value)
    db.commit()
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(get_schedule(db, user, schedule_id))
    db.commit()
