from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.models.encounter import Encounter
from app.models.triage import TriageRecord
from app.models.user import User


OPEN_STATUSES = {"planned", "in-progress"}


def open_encounter(
    db: Session,
    *,
    patient_id: str,
    opened_by: User,
    encounter_class: str = "emergency",
    reason_code: str = "",
) -> Encounter:
    encounter = Encounter(
        patient_id=patient_id,
        encounter_class=encounter_class,
        reason_code=reason_code,
        opened_by=opened_by.id,
        status="in-progress",
    )
    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    return encounter


def assert_encounter_open(db: Session, encounter_id: str, patient_id: str) -> Encounter:
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if encounter.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="Encounter does not belong to this patient")
    if encounter.status not in OPEN_STATUSES:
        raise HTTPException(status_code=409, detail=f"Encounter is {encounter.status}, not open")
    return encounter


def get_or_open_encounter_for_triage(
    db: Session,
    *,
    patient_id: str,
    encounter_id: str | None,
    chief_complaint: str,
    user: User,
) -> Encounter:
    """If encounter_id is provided, validate it; otherwise open a new emergency encounter."""
    if encounter_id:
        return assert_encounter_open(db, encounter_id, patient_id)
    return open_encounter(
        db,
        patient_id=patient_id,
        opened_by=user,
        encounter_class="emergency",
        reason_code=chief_complaint[:500],
    )


def close_encounter(
    db: Session,
    *,
    encounter_id: str,
    disposition: str,
    disposition_notes: str,
    closed_by: User,
) -> Encounter:
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail=f"Encounter already {encounter.status}")

    encounter.status = "completed"
    encounter.disposition = disposition
    encounter.disposition_notes = disposition_notes
    encounter.period_end = datetime.now(timezone.utc)
    encounter.closed_by = closed_by.id

    # Auto-complete linked triage records that are still open
    triage_updates = (
        db.query(TriageRecord)
        .filter(
            TriageRecord.encounter_id == encounter_id,
            TriageRecord.status.in_(["waiting", "in_progress"]),
        )
        .all()
    )
    for record in triage_updates:
        record.status = "completed"

    db.commit()
    db.refresh(encounter)
    return encounter


def update_encounter(
    db: Session,
    *,
    encounter_id: str,
    status: str | None,
    reason_code: str | None,
) -> Encounter:
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if status is not None:
        encounter.status = status
    if reason_code is not None:
        encounter.reason_code = reason_code
    db.commit()
    db.refresh(encounter)
    return encounter


def list_encounters(
    db: Session,
    *,
    patient_id: str | None,
    status: str | None,
    start_after: datetime | None,
    start_before: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[Encounter], int]:
    query = db.query(Encounter)
    if patient_id:
        query = query.filter(Encounter.patient_id == patient_id)
    if status:
        query = query.filter(Encounter.status == status)
    if start_after:
        query = query.filter(Encounter.period_start >= start_after)
    if start_before:
        query = query.filter(Encounter.period_start <= start_before)

    total = query.count()
    encounters = query.order_by(Encounter.period_start.desc()).offset(offset).limit(limit).all()
    return encounters, total


def get_encounter_detail(db: Session, encounter_id: str) -> Encounter:
    encounter = (
        db.query(Encounter)
        .options(
            selectinload(Encounter.triage_records),
            selectinload(Encounter.vitals_records),
            selectinload(Encounter.symptom_checks),
        )
        .filter(Encounter.id == encounter_id)
        .first()
    )
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter
