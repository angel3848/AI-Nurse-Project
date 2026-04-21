from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.allergy import Allergy
from app.models.user import User


def create_allergy(
    db: Session,
    *,
    patient_id: str,
    substance: str,
    category: str,
    criticality: str,
    severity: str,
    reaction: str,
    onset,
    notes: str,
    recorded_by: User,
) -> Allergy:
    allergy = Allergy(
        patient_id=patient_id,
        substance=substance,
        category=category,
        criticality=criticality,
        severity=severity,
        reaction=reaction,
        onset=onset,
        notes=notes,
        recorded_by=recorded_by.id,
        status="active",
    )
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy


def get_allergy(db: Session, allergy_id: str) -> Allergy:
    allergy = db.query(Allergy).filter(Allergy.id == allergy_id).first()
    if allergy is None:
        raise HTTPException(status_code=404, detail="Allergy not found")
    return allergy


def update_allergy(db: Session, allergy_id: str, updates: dict) -> Allergy:
    allergy = get_allergy(db, allergy_id)
    for field, value in updates.items():
        setattr(allergy, field, value)
    db.commit()
    db.refresh(allergy)
    return allergy


def deactivate_allergy(db: Session, allergy_id: str) -> Allergy:
    allergy = get_allergy(db, allergy_id)
    allergy.status = "inactive"
    db.commit()
    db.refresh(allergy)
    return allergy


def list_allergies(
    db: Session,
    *,
    patient_id: str,
    include_inactive: bool,
    limit: int,
    offset: int,
) -> tuple[list[Allergy], int]:
    query = db.query(Allergy).filter(Allergy.patient_id == patient_id)
    if not include_inactive:
        query = query.filter(Allergy.status == "active")
    total = query.count()
    allergies = query.order_by(Allergy.created_at.desc()).offset(offset).limit(limit).all()
    return allergies, total


def check_medication_contraindications(db: Session, *, patient_id: str, medication_name: str) -> list[Allergy]:
    """Return active allergies whose substance appears in the medication name (case-insensitive).

    v1 matching: case-insensitive substring both directions. Good enough to flag
    "penicillin" allergy when prescribing "Amoxicillin-Penicillin"; a real RxNorm
    integration is a future upgrade.
    """
    active = db.query(Allergy).filter(Allergy.patient_id == patient_id, Allergy.status == "active").all()
    med_lower = medication_name.lower()
    matches: list[Allergy] = []
    for a in active:
        sub_lower = a.substance.lower()
        if sub_lower in med_lower or med_lower in sub_lower:
            matches.append(a)
    return matches
