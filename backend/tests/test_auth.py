def test_register_login_me(client):
    body = {"email": "asha@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    token = client.post("/auth/login", json=body).json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "asha@example.com"


def test_duplicate_email(client):
    body = {"email": "asha@example.com", "password": "password123"}
    client.post("/auth/register", json=body)
    assert client.post("/auth/register", json=body).status_code == 409


def test_wrong_password(client):
    client.post("/auth/register", json={"email": "asha@example.com", "password": "password123"})
    r = client.post("/auth/login", json={"email": "asha@example.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_needs_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
