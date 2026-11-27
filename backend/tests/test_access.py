def test_caregiver_cannot_see_other_elders(client, auth, login, elder_with_medicine):
    elder_id, medicine_id = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    dose_id = client.get(f"/elders/{elder_id}/doses", headers=auth).json()[0]["id"]

    other = login("other@example.com")
    assert client.get("/elders", headers=other).json() == []
    for method, url in [
        ("get", f"/elders/{elder_id}"),
        ("delete", f"/elders/{elder_id}"),
        ("get", f"/elders/{elder_id}/medicines"),
        ("get", f"/medicines/{medicine_id}"),
        ("delete", f"/medicines/{medicine_id}"),
        ("get", f"/elders/{elder_id}/next-dose"),
        ("post", f"/elders/{elder_id}/doses/generate?day=2026-03-01"),
        ("post", f"/doses/{dose_id}/take"),
        ("post", f"/doses/{dose_id}/snooze"),
    ]:
        assert getattr(client, method)(url, headers=other).status_code == 404, url


def test_one_caregiver_many_elders(client, auth):
    for name in ["Ajji", "Thatha"]:
        client.post("/elders", json={"name": name}, headers=auth)
    names = [e["name"] for e in client.get("/elders", headers=auth).json()]
    assert names == ["Ajji", "Thatha"]
