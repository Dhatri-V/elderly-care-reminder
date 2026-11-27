import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CaregiverElder, User


def send_telegram(chat_id: str | None, text: str) -> bool:
    if not settings.telegram_bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10).raise_for_status()
    except httpx.HTTPError:
        return False
    return True


def alert_caregivers(db: Session, elder_id: int, text: str) -> None:
    caregivers = (
        db.query(User)
        .join(CaregiverElder, CaregiverElder.user_id == User.id)
        .filter(CaregiverElder.elder_id == elder_id)
    )
    for user in caregivers:
        send_telegram(user.telegram_chat_id, text)
