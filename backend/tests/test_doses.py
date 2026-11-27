from datetime import datetime, timedelta

from app.db import utcnow


def generate(client, auth, elder_id, day="2026-03-01"):
    r = client.post(f"/elders/{elder_id}/doses/generate?day={day}", headers=auth)
    return r.json()["created"]


def test_generate_is_idempotent(client, auth, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    assert generate(client, auth, elder_id) == 2  # ½-0-1 -> morning and night
    assert generate(client, auth, elder_id) == 0

    doses = client.get(f"/elders/{elder_id}/doses", headers=auth).json()
    assert [d["quantity"] for d in doses] == [0.5, 1]
    # 08:00 and 20:00 in India are 02:30 and 14:30 UTC
    assert [d["scheduled_at"] for d in doses] == ["2026-03-01T02:30:00", "2026-03-01T14:30:00"]


def test_generate_skips_days_before_start(client, auth, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    assert generate(client, auth, elder_id, "2025-12-31") == 0


def test_next_dose(client, auth, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    assert client.get(f"/elders/{elder_id}/next-dose", headers=auth).json() is None

    generate(client, auth, elder_id)
    dose = client.get(f"/elders/{elder_id}/next-dose", headers=auth).json()
    assert dose["medicine_name"] == "Metformin"
    assert dose["photo_url"] == "https://example.com/metformin.jpg"
    assert dose["quantity"] == 0.5
    assert dose["food_timing"] == "after"


def test_take_decrements_stock(client, auth, elder_with_medicine):
    elder_id, medicine_id = elder_with_medicine
    generate(client, auth, elder_id)
    dose_id = client.get(f"/elders/{elder_id}/next-dose", headers=auth).json()["dose_id"]

    r = client.post(f"/doses/{dose_id}/take", headers=auth)
    assert r.json()["status"] == "taken"
    assert client.get(f"/medicines/{medicine_id}", headers=auth).json()["stock_count"] == 9.5

    # taking it twice is rejected and doesn't touch stock
    assert client.post(f"/doses/{dose_id}/take", headers=auth).status_code == 409
    assert client.get(f"/medicines/{medicine_id}", headers=auth).json()["stock_count"] == 9.5


def test_snooze_defaults_to_10_minutes(client, auth, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    generate(client, auth, elder_id)
    first = client.get(f"/elders/{elder_id}/next-dose", headers=auth).json()["dose_id"]

    r = client.post(f"/doses/{first}/snooze", headers=auth).json()
    assert r["status"] == "snoozed"
    wait = datetime.fromisoformat(r["snooze_until"]) - utcnow()
    assert timedelta(minutes=9) < wait <= timedelta(minutes=10)

    # while snoozed, the elder sees the next dose
    assert client.get(f"/elders/{elder_id}/next-dose", headers=auth).json()["dose_id"] != first
