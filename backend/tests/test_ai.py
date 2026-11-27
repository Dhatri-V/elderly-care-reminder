"""AI endpoints. The LLM is faked: tests never call a real (paid) API."""

from datetime import timedelta

import chromadb
import pytest
from chromadb import EmbeddingFunction

from app import ai
from app.db import utcnow
from app.models import DoseEvent

WORDS = ["kidney", "sugar", "eye", "walk", "diet", "metformin", "doctor", "water"]


class WordCountEmbedding(EmbeddingFunction):
    """Tiny offline embedding: counts a few words. Good enough to test retrieval."""

    def __init__(self):
        pass

    def __call__(self, input):
        return [[text.lower().count(w) + 0.01 for w in WORDS] for text in input]

    @staticmethod
    def name():
        return "word-count"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return WordCountEmbedding()


@pytest.fixture(autouse=True)
def offline_ai(monkeypatch):
    monkeypatch.setattr(ai, "client", chromadb.EphemeralClient())
    monkeypatch.setattr(ai, "embedding_function", WordCountEmbedding())
    for name in ai.client.list_collections():
        ai.client.delete_collection(getattr(name, "name", name))


@pytest.fixture
def llm(monkeypatch):
    """Fake LLM: returns `llm.reply` and records the prompts it got."""

    class Fake:
        reply = ""
        calls = []

    def fake_chat(messages):
        Fake.calls.append(messages)
        return Fake.reply

    monkeypatch.setattr(ai, "chat", fake_chat)
    return Fake


def test_chat_falls_back_to_next_model(monkeypatch):
    tried = []

    def completion(model, messages, temperature):
        tried.append(model)
        if model.startswith("gemini"):
            raise RuntimeError("quota")

        class R:
            choices = [type("C", (), {"message": type("M", (), {"content": "hi"})})]

        return R

    monkeypatch.setattr(ai.litellm, "completion", completion)
    assert ai.chat([{"role": "user", "content": "x"}]) == "hi"
    assert tried[0].startswith("gemini") and len(tried) == 2


def test_scan_returns_drafts_and_flags_problems(client, auth, llm, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    llm.reply = """```json
    [{"name": "Amlodipine", "strength": "5 mg", "pattern": "1-0-0", "food_timing": "after"},
     {"name": "Pantoprazole", "pattern": null, "food_timing": "before"},
     {"name": null, "pattern": "1-0-1"},
     {"name": "Vitamin D", "pattern": "2-2-2-2", "food_timing": "weird"}]
    ```"""
    r = client.post(
        f"/elders/{elder_id}/prescriptions/scan",
        json={"image": "data:image/jpeg;base64,AAAA"},
        headers=auth,
    )
    assert r.status_code == 200
    items = r.json()
    assert items[0]["name"] == "Amlodipine" and items[0]["problem"] is None
    assert items[1]["problem"] == "Dose pattern could not be read"
    assert items[2]["problem"] == "Medicine name could not be read"
    assert items[3]["food_timing"] == "any" and "pattern" in items[3]["problem"]

    # Nothing was saved: still only the one medicine from the fixture.
    assert len(client.get(f"/elders/{elder_id}/medicines", headers=auth).json()) == 1


def test_scan_unreadable_reply(client, auth, llm, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    llm.reply = "Sorry, I can't read that."
    r = client.post(
        f"/elders/{elder_id}/prescriptions/scan", json={"image": "data:,"}, headers=auth
    )
    assert r.status_code == 503


def test_confirm_saves_medicines_with_schedules(client, auth, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    body = {
        "start_date": "2026-03-01",
        "medicines": [{"name": "Amlodipine", "strength": "5 mg", "pattern": "1-0-0"}],
    }
    r = client.post(f"/elders/{elder_id}/prescriptions/confirm", json=body, headers=auth)
    assert r.status_code == 201
    medicine_id = r.json()[0]["id"]
    schedules = client.get(f"/medicines/{medicine_id}/schedules", headers=auth).json()
    assert schedules[0]["pattern"] == "1-0-0"

    body["medicines"][0]["pattern"] = "bad"
    r = client.post(f"/elders/{elder_id}/prescriptions/confirm", json=body, headers=auth)
    assert r.status_code == 422


def test_ask_uses_documents_and_cites_them(client, auth, llm, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    url = f"/elders/{elder_id}"
    client.post(
        f"{url}/documents",
        json={"title": "Discharge note", "text": "Kidney function is normal. Drink water."},
        headers=auth,
    )
    client.post(
        f"{url}/documents",
        json={"title": "Eye report", "text": "Mild cataract in the left eye."},
        headers=auth,
    )
    assert {d["title"] for d in client.get(f"{url}/documents", headers=auth).json()} == {
        "Discharge note",
        "Eye report",
    }

    llm.reply = "Kidney function is normal [1]."
    r = client.post(f"{url}/ask", json={"question": "How are the kidney results?"}, headers=auth)
    data = r.json()
    assert data["answer"] == "Kidney function is normal [1]."
    assert data["sources"][0] == {
        "n": 1,
        "title": "Discharge note",
        "text": "Kidney function is normal. Drink water.",
    }
    system_prompt = llm.calls[-1][0]["content"]
    assert "[1] (Discharge note)" in system_prompt
    assert "Never give dosage advice" in system_prompt


@pytest.mark.parametrize(
    "question",
    [
        "Can she take 2 tablets instead?",
        "Should I increase the dose?",
        "How much metformin is safe?",
        "Can he skip the night tablet?",
        "Is it ok to give half?",
    ],
)
def test_ask_refuses_dosage_questions(client, auth, llm, elder_with_medicine, question):
    elder_id, _ = elder_with_medicine
    r = client.post(f"/elders/{elder_id}/ask", json={"question": question}, headers=auth)
    assert r.json() == {"answer": ai.NO_DOSAGE_ADVICE, "sources": []}
    assert llm.calls == []  # refused before reaching the model


def test_delete_document_and_access(client, auth, login, llm, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    doc = client.post(
        f"/elders/{elder_id}/documents", json={"title": "Note", "text": "Walk daily."}, headers=auth
    ).json()
    other = login("other@example.com")
    assert client.get(f"/elders/{elder_id}/documents", headers=other).status_code == 404
    assert (
        client.post(f"/elders/{elder_id}/ask", json={"question": "x"}, headers=other).status_code
        == 404
    )

    client.delete(f"/elders/{elder_id}/documents/{doc['id']}", headers=auth)
    assert client.get(f"/elders/{elder_id}/documents", headers=auth).json() == []


def test_weekly_summary(client, auth, llm, db, elder_with_medicine):
    elder_id, _ = elder_with_medicine
    r = client.get(f"/elders/{elder_id}/summary/weekly", headers=auth)
    assert r.json() == {"stats": [], "summary": "No doses were due in the last 7 days."}

    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    statuses = ["taken", "missed"]
    for i, dose in enumerate(db.query(DoseEvent).all()):
        dose.scheduled_at = utcnow() - timedelta(days=1, hours=i)
        dose.status = statuses[i]
    db.commit()

    llm.reply = "Ajji took most medicines."
    data = client.get(f"/elders/{elder_id}/summary/weekly", headers=auth).json()
    assert data["stats"] == [{"medicine": "Metformin", "taken": 1, "missed": 1, "total": 2}]
    assert data["summary"] == "Ajji took most medicines."


def test_summary_still_shows_numbers_when_ai_is_down(
    client, auth, db, monkeypatch, elder_with_medicine
):
    def down(messages):
        raise ai.AIError("AI is not available right now. Please try again later.")

    monkeypatch.setattr(ai, "chat", down)
    elder_id, _ = elder_with_medicine
    client.post(f"/elders/{elder_id}/doses/generate?day=2026-03-01", headers=auth)
    data = client.get(f"/elders/{elder_id}/summary/weekly", headers=auth).json()
    assert data["stats"] == []  # March doses are older than 7 days
    for dose in db.query(DoseEvent).all():
        dose.scheduled_at = utcnow() - timedelta(days=1)
    db.commit()
    data = client.get(f"/elders/{elder_id}/summary/weekly", headers=auth).json()
    assert data["stats"][0]["total"] == 2
    assert data["summary"] == "AI is not available right now. Please try again later."
