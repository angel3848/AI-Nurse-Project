from fastapi import APIRouter

from app.schemas.metrics import BMIRequest, BMIResponse
from app.services.bmi_calculator import assess_bmi

router = APIRouter(prefix="/api/v1/metrics", tags=["Health Metrics"])


@router.post("/bmi", response_model=BMIResponse)
def calculate_bmi(request: BMIRequest) -> BMIResponse:
    """Calculate BMI from height and weight, returning category and interpretation."""
    return assess_bmi(request)
