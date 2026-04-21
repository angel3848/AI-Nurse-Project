import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.triage import SymptomCheckRecord
from app.models.user import User
from app.utils.auth import get_current_user
from app.schemas.symptom import (
    ConditionInfo,
    ConditionsListResponse,
    SymptomCheckRequest,
    SymptomCheckResponse,
)
from app.services import encounter_service
from app.services.symptom_checker import CONDITION_DATABASE, check_symptoms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/symptoms", tags=["Symptoms"])


@router.post("/check", response_model=SymptomCheckResponse)
def symptom_check(
    request: SymptomCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SymptomCheckResponse:
    """Analyze reported symptoms and suggest possible conditions."""
    result = check_symptoms(request)

    if settings.ai_analysis_enabled and settings.anthropic_api_key:
        try:
            from app.services.ai_analyzer import analyze_symptoms_with_ai

            rule_based_results = {
                "possible_conditions": [c.model_dump() for c in result.possible_conditions],
                "urgency": result.urgency,
                "recommended_action": result.recommended_action,
            }
            result.ai_analysis = analyze_symptoms_with_ai(
                symptoms=request.symptoms,
                duration_days=request.duration_days,
                severity=request.severity,
                age=request.age,
                additional_info=request.additional_info,
                rule_based_results=rule_based_results,
            )
        except Exception:
            logger.exception("AI analysis failed, continuing without it")

    if request.patient_id:
        if request.encounter_id:
            encounter_service.assert_encounter_open(db, request.encounter_id, request.patient_id)
        record = SymptomCheckRecord(
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            symptoms=request.symptoms,
            duration_days=request.duration_days,
            severity=request.severity,
            urgency=result.urgency,
            conditions_found=[c.model_dump() for c in result.possible_conditions],
            recommended_action=result.recommended_action,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result.id = record.id

    return result


@router.get("/conditions", response_model=ConditionsListResponse)
def list_conditions(
    category: str | None = Query(None, description="Filter by category"),
) -> ConditionsListResponse:
    """List all known conditions in the symptom checker database."""
    conditions = []
    for required_symptoms, name, description, cat in CONDITION_DATABASE:
        if category and cat != category:
            continue
        conditions.append(
            ConditionInfo(
                condition=name,
                category=cat,
                description=description,
                required_symptoms=sorted(required_symptoms),
            )
        )

    return ConditionsListResponse(conditions=conditions, total=len(conditions))
