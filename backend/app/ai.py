"""AI helpers: LLM calls with fallback, prescription reading, per-elder document Q&A."""

import json
import logging
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as CallTimeout

import chromadb

# Use the price list bundled with LiteLLM instead of downloading it from GitHub on start.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

log = logging.getLogger(__name__)
# Newer models reject some settings (like temperature); drop them instead of failing.
litellm.drop_params = True


class AIError(Exception):
    pass


def api_key_for(model: str) -> str | None:
    """Keys live in settings (.env); LiteLLM would otherwise only look in os.environ."""
    if model.startswith("gemini/"):
        return settings.gemini_api_key or None
    if model.startswith("openrouter/"):
        return settings.openrouter_api_key or None
    return None


def ask_model(model: str, messages: list[dict]) -> str:
    """One call with a hard time limit.

    LiteLLM's own timeout doesn't always fire on a stalled connection, so the call runs
    in a thread and we stop waiting for it after the limit.
    """
    limit = settings.ai_timeout_seconds
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(
        litellm.completion,
        model=model,
        messages=messages,
        temperature=0.2,
        api_key=api_key_for(model),
        timeout=limit,
        num_retries=0,
    )
    pool.shutdown(wait=False)  # don't block on a stuck call
    try:
        response = future.result(timeout=limit)
    except CallTimeout:
        raise TimeoutError(f"no answer within {limit:g} s") from None
    return response.choices[0].message.content


def chat(messages: list[dict]) -> str:
    """Ask the first model that works: Gemini first, then the fallbacks."""
    for model in settings.llm_models.split(","):
        model = model.strip()
        try:
            return ask_model(model, messages)
        except Exception as e:  # any provider error or timeout: try the next model
            log.warning("AI model %s failed: %s", model, e)
    raise AIError("AI is not available right now. Please try again later.")


# ---------- prescription scan ----------

SCAN_PROMPT = """Read this prescription and list the medicines on it.
Reply with only a JSON list. Each item has:
  "name": medicine name,
  "strength": e.g. "500 mg", or null,
  "pattern": morning-afternoon-night tablets like "1-0-1" (use 0.5 for half), or null,
  "food_timing": "before", "after", "with" or "any".
If you can't read something, use null. Do not guess."""


def scan_prescription(image_data_url: str) -> list[dict]:
    reply = chat(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SCAN_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ]
    )
    text = reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        raise AIError("Could not read the prescription. Please try a clearer photo.") from None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


# ---------- per-elder documents and Q&A ----------

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
client = None
embedding_function = None  # None: Chroma's built-in local embedding model


def collection(elder_id: int):
    global client
    if client is None:
        client = chromadb.PersistentClient(path=settings.chroma_dir)
    options = {"embedding_function": embedding_function} if embedding_function else {}
    return client.get_or_create_collection(f"elder_{elder_id}", **options)


def add_document(elder_id: int, title: str, text: str) -> str:
    doc_id = uuid.uuid4().hex[:12]
    chunks = splitter.split_text(text)
    collection(elder_id).add(
        ids=[f"{doc_id}-{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[{"doc_id": doc_id, "title": title} for _ in chunks],
    )
    return doc_id


def list_documents(elder_id: int) -> list[dict]:
    metadatas = collection(elder_id).get(include=["metadatas"])["metadatas"]
    unique = {m["doc_id"]: m["title"] for m in metadatas}
    return [{"id": doc_id, "title": title} for doc_id, title in unique.items()]


def delete_document(elder_id: int, doc_id: str) -> None:
    collection(elder_id).delete(where={"doc_id": doc_id})


DOSAGE_QUESTION = re.compile(
    r"\b(dose|doses|dosage|how (many|much)|increase|decrease|reduce|double|skip|"
    r"stop taking|overdose|extra (tablet|pill)|mg|"
    r"(take|give) (\d|half|one|two|three|more|less|fewer))\b",
    re.IGNORECASE,
)
NO_DOSAGE_ADVICE = "I can't give advice about doses. Please ask the doctor or pharmacist."

QA_PROMPT = """You help a caregiver understand an elderly person's medical documents.
Answer using ONLY the numbered sources below and cite them like [1].
If the sources don't answer the question, say you couldn't find it.
Never give dosage advice (how much to take, changing, skipping or stopping a medicine):
say to ask the doctor or pharmacist instead. Keep the answer short and simple.

Sources:
{sources}"""


def ask(elder_id: int, question: str) -> dict:
    if DOSAGE_QUESTION.search(question):
        return {"answer": NO_DOSAGE_ADVICE, "sources": []}

    docs = collection(elder_id)
    if docs.count() == 0:
        return {"answer": "There are no documents for this person yet.", "sources": []}

    found = docs.query(query_texts=[question], n_results=min(4, docs.count()))
    sources = [
        {"n": i + 1, "title": meta["title"], "text": text}
        for i, (text, meta) in enumerate(
            zip(found["documents"][0], found["metadatas"][0], strict=True)
        )
    ]
    numbered = "\n\n".join(f"[{s['n']}] ({s['title']}) {s['text']}" for s in sources)
    answer = chat(
        [
            {"role": "system", "content": QA_PROMPT.format(sources=numbered)},
            {"role": "user", "content": question},
        ]
    )
    return {"answer": answer, "sources": sources}


# ---------- weekly summary ----------

SUMMARY_PROMPT = """Write a short, kind weekly summary (3-5 sentences) for a caregiver about
how well {name} took their medicines in the last 7 days, from this data:
{stats}
Point out medicines that were missed often. Do not give medical or dosage advice."""


def weekly_summary(name: str, stats: list[dict]) -> str:
    return chat(
        [{"role": "user", "content": SUMMARY_PROMPT.format(name=name, stats=json.dumps(stats))}]
    )
