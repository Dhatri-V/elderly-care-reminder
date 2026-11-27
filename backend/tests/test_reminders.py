from datetime import timedelta

import pytest

from app import notify
from app.db import utcnow
from app.models import DoseEvent
from app.services import mark_missed


@pytest.fixture
def sent(monkeypatch):
    """Capture Telegram messages instead of sending them."""
    messages = []
    monkeypatch.setattr(notify, "send_telegram", lambda chat_id, text: messages.append(text))
    return messages


@pytest.fixture
def doses(client, auth, elder_with_medicine, db):
    elder_id, _ = elder_with_medicine
    client.put("/auth/me/telegram", json={"chat_id": "12345"}, headers=auth)
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    return db.query(DoseEvent).order_by(DoseEvent.scheduled_at).all()


def test_overdue_dose_is_marked_missed_and_alerts(db, doses, sent):
    morning, night = doses
    morning.scheduled_at = utcnow() - timedelta(minutes=31)
    night.scheduled_at = utcnow() - timedelta(minutes=20)  # not 30 minutes yet
    db.commit()

    assert mark_missed(db) == 1
    assert morning.status == "missed"
    assert night.status == "pending"
    assert sent == [f"Ajji missed 0.5 x Metformin (due {_ist(morning.scheduled_at)})."]


def test_snoozed_dose_is_missed_30_minutes_after_snooze(db, doses, sent):
    morning, night = doses
    night.scheduled_at = utcnow() + timedelta(hours=5)
    morning.scheduled_at = utcnow() - timedelta(hours=2)
    morning.status = "snoozed"
    morning.snooze_until = utcnow() - timedelta(minutes=10)
    db.commit()
    assert mark_missed(db) == 0  # snoozed 10 minutes ago: still has time

    morning.snooze_until = utcnow() - timedelta(minutes=31)
    db.commit()
    assert mark_missed(db) == 1
    assert morning.status == "missed"


def test_refill_alert_sent_once(client, auth, db, doses, sent):
    medicine_id = doses[0].medicine_id
    medicine = {
        "name": "Metformin",
        "food_timing": "after",
        "stock_count": 1.5,
        "refill_threshold": 1,
    }
    client.put(f"/medicines/{medicine_id}", json=medicine, headers=auth)

    client.post(f"/doses/{doses[0].id}/take", headers=auth)  # 1.5 -> 1, at threshold
    client.post(f"/doses/{doses[1].id}/take", headers=auth)  # 1 -> 0
    assert sent == ["Refill needed: Metformin for Ajji, 1 left."]

    # Restocking resets it
    client.put(f"/medicines/{medicine_id}", json={**medicine, "stock_count": 30}, headers=auth)
    assert client.get(f"/medicines/{medicine_id}", headers=auth).json()["stock_count"] == 30
    assert doses[0].medicine.refill_alert_sent is False


def _ist(utc_time):
    return (utc_time + timedelta(hours=5, minutes=30)).strftime("%H:%M")
