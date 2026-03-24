import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.triage import TriageRecord
from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_engine import perform_triage

router = APIRouter(prefix="/api/v1/triage", tags=["Triage"])


@router.post("", response_model=TriageResponse)
def create_triage(request: TriageRequest, db: Session = Depends(get_db)) -> TriageResponse:
    """Submit a triage assessment and receive a priority classification."""
    result = perform_triage(request)

    if request.patient_id:
        record = TriageRecord(
            patient_id=request.patient_id,
            chief_complaint=request.chief_complaint,
            symptoms=json.dumps(request.symptoms),
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
            flags=json.dumps(result.flags),
            notes=request.notes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result.id = record.id

    return result
