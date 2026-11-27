from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import ai
from app.db import get_db, utcnow
from app.deps import check_access, current_user
from app.models import DoseEvent, Medicine, Schedule, User
from app.pattern import parse_pattern
from app.schemas import (
    AskIn,
    ConfirmIn,
    DocumentIn,
    MedicineOut,
    PrescriptionItem,
    ScanIn,
)

router = APIRouter(prefix="/elders/{elder_id}", tags=["ai"])


def ai_call(fn, *args):
    try:
        return fn(*args)
    except ai.AIError as e:
        raise HTTPException(503, str(e)) from e


@router.post("/prescriptions/scan", response_model=list[PrescriptionItem])
def scan(
    elder_id: int, body: ScanIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Read a prescription photo into draft medicines. Saves nothing."""
    check_access(db, user, elder_id)
    items = []
    for raw in ai_call(ai.scan_prescription, body.image):
        item = PrescriptionItem(
            name=raw.get("name"),
            strength=raw.get("strength"),
            pattern=raw.get("pattern"),
            food_timing=raw.get("food_timing")
            if raw.get("food_timing") in ("before", "after", "with")
            else "any",
        )
        if not item.name:
            item.problem = "Medicine name could not be read"
        elif not item.pattern:
            item.problem = "Dose pattern could not be read"
        else:
            try:
                parse_pattern(item.pattern)
            except ValueError as e:
                item.problem = str(e)
        items.append(item)
    return items


@router.post("/prescriptions/confirm", response_model=list[MedicineOut], status_code=201)
def confirm(
    elder_id: int,
    body: ConfirmIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Save the medicines the caregiver checked, each with its schedule."""
    check_access(db, user, elder_id)
    medicines = []
    for item in body.medicines:
        medicine = Medicine(elder_id=elder_id, **item.model_dump(exclude={"pattern"}))
        medicine.schedules.append(Schedule(pattern=item.pattern, start_date=body.start_date))
        db.add(medicine)
        medicines.append(medicine)
    db.commit()
    return medicines


@router.post("/documents", status_code=201)
def add_document(
    elder_id: int,
    body: DocumentIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    check_access(db, user, elder_id)
    return {"id": ai.add_document(elder_id, body.title, body.text), "title": body.title}


@router.get("/documents")
def list_documents(
    elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    check_access(db, user, elder_id)
    return ai.list_documents(elder_id)


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    elder_id: int, doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    check_access(db, user, elder_id)
    ai.delete_document(elder_id, doc_id)


@router.post("/ask")
def ask(
    elder_id: int, body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Answer a question from this elder's documents, with numbered sources."""
    check_access(db, user, elder_id)
    return ai_call(ai.ask, elder_id, body.question)


@router.get("/summary/weekly")
def weekly_summary(
    elder_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    elder = check_access(db, user, elder_id)
    now = utcnow()
    doses = (
        db.query(DoseEvent)
        .filter(DoseEvent.elder_id == elder_id)
        .filter(DoseEvent.scheduled_at >= now - timedelta(days=7), DoseEvent.scheduled_at <= now)
        .all()
    )
    counts: dict[str, Counter] = {}
    for dose in doses:
        counts.setdefault(dose.medicine.name, Counter())[dose.status] += 1
    stats = [
        {"medicine": name, "taken": c["taken"], "missed": c["missed"], "total": c.total()}
        for name, c in counts.items()
    ]
    if not stats:
        return {"stats": [], "summary": "No doses were due in the last 7 days."}
    try:
        summary = ai.weekly_summary(elder.name, stats)
    except ai.AIError as e:
        summary = str(e)  # still show the numbers
    return {"stats": stats, "summary": summary}
