import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.triage import SymptomCheckRecord
from app.schemas.symptom import SymptomCheckRequest, SymptomCheckResponse
from app.services.symptom_checker import check_symptoms

router = APIRouter(prefix="/api/v1/symptoms", tags=["Symptoms"])


@router.post("/check", response_model=SymptomCheckResponse)
def symptom_check(request: SymptomCheckRequest, db: Session = Depends(get_db)) -> SymptomCheckResponse:
    """Analyze reported symptoms and suggest possible conditions."""
    result = check_symptoms(request)

    if request.patient_id:
        record = SymptomCheckRecord(
            patient_id=request.patient_id,
            symptoms=json.dumps(request.symptoms),
            duration_days=request.duration_days,
            severity=request.severity,
            urgency=result.urgency,
            conditions_found=json.dumps([c.model_dump() for c in result.possible_conditions]),
            recommended_action=result.recommended_action,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result.id = record.id

    return result
