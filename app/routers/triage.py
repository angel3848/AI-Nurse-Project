from fastapi import APIRouter

from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_engine import perform_triage

router = APIRouter(prefix="/api/v1/triage", tags=["Triage"])


@router.post("", response_model=TriageResponse)
def create_triage(request: TriageRequest) -> TriageResponse:
    """Submit a triage assessment and receive a priority classification."""
    return perform_triage(request)
