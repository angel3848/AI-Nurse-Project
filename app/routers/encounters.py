import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.routers.ws import queue_manager
from app.schemas.encounter import (
    EncounterClose,
    EncounterCreate,
    EncounterDetailResponse,
    EncounterListResponse,
    EncounterResponse,
    EncounterUpdate,
    STATUS_PATTERN,
)
from app.services import encounter_service
from app.services.audit_logger import log_action
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/encounters", tags=["Encounters"])


def _notify(event: str, encounter_id: str) -> None:
    """Fire-and-forget WebSocket broadcast; generic queue_updated fallback for old clients."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(queue_manager.broadcast({"event": event, "encounter_id": encounter_id}))
        loop.create_task(queue_manager.broadcast({"event": "queue_updated"}))
    except RuntimeError:
        pass


def _patient_or_404(db: Session, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=EncounterResponse, status_code=201)
def create_encounter(
    body: EncounterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Encounter:
    """Open a new encounter for a patient."""
    _patient_or_404(db, body.patient_id)

    encounter = encounter_service.open_encounter(
        db,
        patient_id=body.patient_id,
        opened_by=current_user,
        encounter_class=body.encounter_class,
        reason_code=body.reason_code,
    )

    log_action(
        db,
        action="create",
        resource_type="encounter",
        resource_id=encounter.id,
        detail=f"Opened encounter for patient {body.patient_id}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    _notify("encounter_opened", encounter.id)
    return encounter


@router.get("", response_model=EncounterListResponse)
def list_encounters_endpoint(
    patient_id: str | None = Query(None),
    status: str | None = Query(None, pattern=STATUS_PATTERN),
    start_after: datetime | None = Query(None),
    start_before: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List encounters with optional filters. Patients may only list their own."""
    if current_user.role == "patient":
        own_patient = (
            db.query(Patient)
            .filter(Patient.user_id == current_user.id, Patient.is_deleted == False)  # noqa: E712
            .first()
        )
        if own_patient is None:
            raise HTTPException(status_code=403, detail="No patient record for this user")
        if patient_id and patient_id != own_patient.id:
            raise HTTPException(status_code=403, detail="Access denied")
        patient_id = own_patient.id

    encounters, total = encounter_service.list_encounters(
        db,
        patient_id=patient_id,
        status=status,
        start_after=start_after,
        start_before=start_before,
        limit=limit,
        offset=offset,
    )
    return {"encounters": encounters, "total": total}


@router.get("/{encounter_id}", response_model=EncounterDetailResponse)
def get_encounter(
    encounter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Encounter:
    """Get full encounter detail with nested triage/vitals/symptom records."""
    encounter = encounter_service.get_encounter_detail(db, encounter_id)

    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
        if patient is None or patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    log_action(
        db,
        action="read",
        resource_type="encounter",
        resource_id=encounter_id,
        detail=f"Viewed encounter for patient {encounter.patient_id}",
        user=current_user,
    )
    return encounter


@router.patch("/{encounter_id}", response_model=EncounterResponse)
def update_encounter_endpoint(
    encounter_id: str,
    body: EncounterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Encounter:
    """Update encounter status or reason_code."""
    encounter = encounter_service.update_encounter(
        db,
        encounter_id=encounter_id,
        status=body.status,
        reason_code=body.reason_code,
    )
    log_action(
        db,
        action="update",
        resource_type="encounter",
        resource_id=encounter_id,
        detail=f"Updated fields: {', '.join(body.model_dump(exclude_unset=True).keys())}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    _notify("encounter_updated", encounter_id)
    return encounter


@router.patch("/{encounter_id}/close", response_model=EncounterResponse)
def close_encounter_endpoint(
    encounter_id: str,
    body: EncounterClose,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor", "admin")),
) -> Encounter:
    """Close an encounter with a disposition. Doctor or admin only."""
    encounter = encounter_service.close_encounter(
        db,
        encounter_id=encounter_id,
        disposition=body.disposition,
        disposition_notes=body.disposition_notes,
        closed_by=current_user,
    )
    log_action(
        db,
        action="close",
        resource_type="encounter",
        resource_id=encounter_id,
        detail=f"Closed with disposition: {body.disposition}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    _notify("encounter_closed", encounter_id)
    return encounter
