from fastapi import APIRouter

from app.schemas.symptom import SymptomCheckRequest, SymptomCheckResponse
from app.services.symptom_checker import check_symptoms

router = APIRouter(prefix="/api/v1/symptoms", tags=["Symptoms"])


@router.post("/check", response_model=SymptomCheckResponse)
def symptom_check(request: SymptomCheckRequest) -> SymptomCheckResponse:
    """Analyze reported symptoms and suggest possible conditions."""
    return check_symptoms(request)
