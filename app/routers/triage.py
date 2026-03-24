from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.triage import TriageRecord
from app.models.user import User
from app.schemas.triage import (
    TriageQueueItem,
    TriageQueueResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.triage_engine import perform_triage
from app.utils.auth import require_role

router = APIRouter(prefix="/api/v1/triage", tags=["Triage"])


@router.post("", response_model=TriageResponse)
def create_triage(request: TriageRequest, db: Session = Depends(get_db)) -> TriageResponse:
    """Submit a triage assessment and receive a priority classification."""
    result = perform_triage(request)

    if request.patient_id:
        record = TriageRecord(
            patient_id=request.patient_id,
            chief_complaint=request.chief_complaint,
            symptoms=request.symptoms,
            symptom_duration=request.symptom_duration,
            pain_scale=request.pain_scale,
            heart_rate=request.vitals.heart_rate,
            bp_systolic=request.vitals.blood_pressure_systolic,
            bp_diastolic=request.vitals.blood_pressure_diastolic,
            temperature_c=request.vitals.temperature_c,
            respiratory_rate=request.vitals.respiratory_rate,
            oxygen_saturation=request.vitals.oxygen_saturation,
            priority_level=result.priority_level,
            priority_label=result.priority_label,
            recommended_action=result.recommended_action,
            flags=result.flags,
            notes=request.notes,
            status="waiting",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result.id = record.id

    return result


@router.get("/queue", response_model=TriageQueueResponse)
def get_triage_queue(
    status: str = Query("waiting", pattern="^(waiting|in_progress|completed)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> TriageQueueResponse:
    """View current triage queue sorted by priority. Requires nurse, doctor, or admin role."""
    records = (
        db.query(TriageRecord, Patient.full_name)
        .join(Patient, TriageRecord.patient_id == Patient.id)
        .filter(TriageRecord.status == status)
        .order_by(TriageRecord.priority_level.asc(), TriageRecord.created_at.asc())
        .all()
    )

    now = datetime.now(timezone.utc)
    queue = []
    for record, patient_name in records:
        created = record.created_at.replace(tzinfo=timezone.utc) if record.created_at.tzinfo is None else record.created_at
        wait_minutes = int((now - created).total_seconds() / 60)
        color_map = {1: "red", 2: "orange", 3: "yellow", 4: "green", 5: "blue"}
        queue.append(TriageQueueItem(
            id=record.id,
            patient_id=record.patient_id,
            patient_name=patient_name,
            priority_level=record.priority_level,
            priority_label=record.priority_label,
            priority_color=color_map.get(record.priority_level, "blue"),
            chief_complaint=record.chief_complaint,
            created_at=record.created_at,
            wait_time_minutes=wait_minutes,
        ))

    return TriageQueueResponse(queue=queue, total=len(queue))


@router.put("/{triage_id}/status")
def update_triage_status(
    triage_id: str,
    status: str = Query(..., pattern="^(waiting|in_progress|completed)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> dict:
    """Update a triage record's status. Requires nurse, doctor, or admin role."""
    record = db.query(TriageRecord).filter(TriageRecord.id == triage_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Triage record not found")
    record.status = status
    db.commit()
    return {"id": triage_id, "status": status}
