from datetime import timedelta

from analytics import adherence, daily, load_doses, low_stock
from app.db import utcnow
from app.models import DoseEvent


def test_adherence_and_low_stock(client, auth, db, elder_with_medicine):
    elder_id, medicine_id = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-02", headers=auth)
    statuses = ["taken", "taken", "missed", "pending"]
    for i, dose in enumerate(db.query(DoseEvent).order_by(DoseEvent.id)):
        dose.scheduled_at = utcnow() - timedelta(days=1 + i // 2, hours=i)
        dose.status = statuses[i]
    db.commit()

    doses = load_doses(db, days=7)
    assert len(doses) == 4

    table = adherence(doses)
    row = table.iloc[0]
    assert (row["elder"], row["medicine"]) == ("Ajji", "Metformin")
    assert (row["taken"], row["missed"], row["adherence %"]) == (2, 1, 67)

    per_day = daily(doses)
    assert per_day["taken"].sum() == 2 and per_day["missed"].sum() == 1

    assert low_stock(db).empty
    medicine = {"name": "Metformin", "stock_count": 2, "refill_threshold": 5}
    client.put(f"/medicines/{medicine_id}", json=medicine, headers=auth)
    assert low_stock(db)["medicine"].tolist() == ["Metformin"]


def test_days_are_in_the_elders_timezone(client, auth, db, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    dose = db.query(DoseEvent).first()
    # 20:00 UTC yesterday is 01:30 today in India.
    yesterday = utcnow() - timedelta(days=1)
    dose.scheduled_at = yesterday.replace(hour=20, minute=0)
    dose.status = "taken"
    db.commit()
    assert load_doses(db, days=7)["day"].tolist() == [(yesterday + timedelta(days=1)).date()]


def test_old_doses_are_left_out(client, auth, db, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    assert load_doses(db, days=7).empty  # March is months ago
