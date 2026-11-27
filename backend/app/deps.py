from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CaregiverElder, Elder, User
from app.security import read_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = read_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user


def check_access(db: Session, user: User, elder_id: int) -> Elder:
    """Return the elder if this caregiver is linked to them, otherwise 404."""
    link = db.query(CaregiverElder).filter_by(user_id=user.id, elder_id=elder_id).first()
    if link is None:
        raise HTTPException(404, "Elder not found")
    return db.get(Elder, elder_id)
