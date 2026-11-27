import os

os.environ["DATABASE_URL"] = "sqlite://"  # keep app import from creating a db file
os.environ["RUN_SCHEDULER"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    """Register and log in a caregiver, returning auth headers."""

    def _login(email="carer@example.com", password="password123"):
        client.post("/auth/register", json={"email": email, "password": password})
        token = client.post("/auth/login", json={"email": email, "password": password}).json()
        return {"Authorization": f"Bearer {token['access_token']}"}

    return _login


@pytest.fixture
def auth(login):
    return login()


@pytest.fixture
def elder_with_medicine(client, auth):
    """An elder with one medicine (stock 10) taken ½-0-1 from 2026-01-01."""
    elder = client.post("/elders", json={"name": "Ajji", "language": "kn"}, headers=auth).json()
    medicine = client.post(
        f"/elders/{elder['id']}/medicines",
        json={
            "name": "Metformin",
            "strength": "500 mg",
            "photo_url": "https://example.com/metformin.jpg",
            "food_timing": "after",
            "stock_count": 10,
        },
        headers=auth,
    ).json()
    client.post(
        f"/medicines/{medicine['id']}/schedules",
        json={"pattern": "½-0-1", "start_date": "2026-01-01"},
        headers=auth,
    )
    return elder["id"], medicine["id"]
