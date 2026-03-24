from pydantic import BaseModel, Field


class SymptomCheckRequest(BaseModel):
    patient_id: str | None = Field(None, description="Optional patient ID to persist the symptom check")
    symptoms: list[str] = Field(..., min_length=1, max_length=20)
    duration_days: int = Field(..., gt=0, le=365)
    severity: str = Field(..., pattern="^(mild|moderate|severe)$")
    age: int = Field(..., gt=0, le=150)
    additional_info: str = Field("", max_length=2000)


class PossibleCondition(BaseModel):
    condition: str
    probability: str
    description: str
    category: str


class SymptomCheckResponse(BaseModel):
    id: str | None = None
    possible_conditions: list[PossibleCondition]
    recommended_action: str
    urgency: str
    disclaimer: str = (
        "This is not a medical diagnosis. Please consult a healthcare "
        "professional for proper evaluation and treatment."
    )
