from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import check_access, current_user
from app.models import CaregiverElder, Elder, User
from app.schemas import ElderIn, ElderOut

router = APIRouter(prefix="/elders", tags=["elders"])


@router.post("", response_model=ElderOut, status_code=201)
def create_elder(body: ElderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    elder = Elder(**body.model_dump())
    db.add(elder)
    db.flush()
    db.add(CaregiverElder(user_id=user.id, elder_id=elder.id))
    db.commit()
    return elder


@router.get("", response_model=list[ElderOut])
def list_elders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return (
        db.query(Elder)
        .join(CaregiverElder, CaregiverElder.elder_id == Elder.id)
        .filter(CaregiverElder.user_id == user.id)
        .order_by(Elder.id)
        .all()
    )


@router.get("/{elder_id}", response_model=ElderOut)
def get_elder(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return check_access(db, user, elder_id)


@router.put("/{elder_id}", response_model=ElderOut)
def update_elder(
    elder_id: int, body: ElderIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    elder = check_access(db, user, elder_id)
    for key, value in body.model_dump().items():
        setattr(elder, key, value)
    db.commit()
    return elder


@router.delete("/{elder_id}", status_code=204)
def delete_elder(elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(check_access(db, user, elder_id))
    db.commit()
