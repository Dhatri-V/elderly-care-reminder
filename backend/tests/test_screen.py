import pytest

from app import notify


@pytest.fixture
def screen(client, auth, elder_with_medicine):
    """Headers for the elder's device, after today's doses are generated."""
    elder_id, _ = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    token = client.get(f"/elders/{elder_id}", headers=auth).json()["screen_token"]
    return {"X-Screen-Token": token}


def test_screen_shows_next_dose(client, screen):
    data = client.get("/screen", headers=screen).json()
    assert data["elder_name"] == "Ajji"
    assert data["language"] == "kn"
    assert data["next_dose"]["medicine_name"] == "Metformin"
    assert data["next_dose"]["quantity"] == 0.5
    assert data["next_appointment"] is None


def test_screen_take_and_snooze(client, screen):
    first = client.get("/screen", headers=screen).json()["next_dose"]["dose_id"]
    assert client.post(f"/screen/doses/{first}/take", headers=screen).json()["status"] == "taken"
    assert client.post(f"/screen/doses/{first}/take", headers=screen).status_code == 409

    second = client.get("/screen", headers=screen).json()["next_dose"]["dose_id"]
    r = client.post(f"/screen/doses/{second}/snooze", headers=screen)
    assert r.json()["status"] == "snoozed"
    assert client.get("/screen", headers=screen).json()["next_dose"] is None


def test_bad_or_old_token_rejected(client, auth, screen, elder_with_medicine):
    assert client.get("/screen", headers={"X-Screen-Token": "nope"}).status_code == 401
    elder_id, _ = elder_with_medicine
    client.post(f"/elders/{elder_id}/screen-token", headers=auth)
    assert client.get("/screen", headers=screen).status_code == 401


def test_screen_cannot_touch_other_elders_doses(client, auth, login, screen):
    other = login("other@example.com")
    elder = client.post("/elders", json={"name": "Thatha"}, headers=other).json()
    medicine = client.post(
        f"/elders/{elder['id']}/medicines", json={"name": "Aspirin"}, headers=other
    ).json()
    client.post(
        f"/medicines/{medicine['id']}/schedules",
        json={"pattern": "1-0-0", "start_date": "2026-01-01"},
        headers=other,
    )
    client.post(f"/elders/{elder['id']}/doses/generate?day=2026-03-01", headers=other)
    dose_id = client.get(f"/elders/{elder['id']}/doses", headers=other).json()[0]["id"]

    assert client.post(f"/screen/doses/{dose_id}/take", headers=screen).status_code == 404


def test_sos_alerts_caregivers(client, auth, screen, monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "send_telegram", lambda chat_id, text: sent.append(text))
    client.put("/auth/me/telegram", json={"chat_id": "1"}, headers=auth)
    assert client.post("/screen/sos", headers=screen).json() == {"ok": True}
    assert sent == ["SOS! Ajji pressed the emergency button."]


def test_appointments(client, auth, login, screen, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    url = f"/elders/{elder_id}/appointments"
    client.post(url, json={"title": "Old checkup", "starts_at": "2020-01-01T10:00"}, headers=auth)
    r = client.post(
        url,
        json={"title": "Eye checkup", "doctor": "Dr. Rao", "starts_at": "2099-01-05T10:30"},
        headers=auth,
    )
    assert r.status_code == 201
    appointment_id = r.json()["id"]

    assert len(client.get(url, headers=auth).json()) == 2
    assert (
        client.get("/screen", headers=screen).json()["next_appointment"]["title"] == "Eye checkup"
    )

    updated = {"title": "Eye checkup", "starts_at": "2099-01-06T09:00"}
    r = client.put(f"/appointments/{appointment_id}", json=updated, headers=auth)
    assert r.json()["starts_at"] == "2099-01-06T09:00:00"

    other = login("other@example.com")
    assert client.get(url, headers=other).status_code == 404
    assert client.delete(f"/appointments/{appointment_id}", headers=other).status_code == 404
    assert client.delete(f"/appointments/{appointment_id}", headers=auth).status_code == 204
