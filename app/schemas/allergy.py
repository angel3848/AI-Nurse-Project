from datetime import date, datetime

from pydantic import BaseModel, Field

CATEGORY_PATTERN = "^(medication|food|environment|biologic)$"
CRITICALITY_PATTERN = "^(low|high|unable-to-assess)$"
SEVERITY_PATTERN = "^(mild|moderate|severe)$"
STATUS_PATTERN = "^(active|inactive|resolved|entered-in-error)$"


class AllergyCreate(BaseModel):
    patient_id: str = Field(..., min_length=1)
    substance: str = Field(..., min_length=1, max_length=200)
    category: str = Field("medication", pattern=CATEGORY_PATTERN)
    criticality: str = Field("unable-to-assess", pattern=CRITICALITY_PATTERN)
    severity: str = Field("moderate", pattern=SEVERITY_PATTERN)
    reaction: str = Field("", max_length=500)
    onset: date | None = None
    notes: str = Field("", max_length=2000)


class AllergyUpdate(BaseModel):
    substance: str | None = Field(None, min_length=1, max_length=200)
    category: str | None = Field(None, pattern=CATEGORY_PATTERN)
    criticality: str | None = Field(None, pattern=CRITICALITY_PATTERN)
    severity: str | None = Field(None, pattern=SEVERITY_PATTERN)
    reaction: str | None = Field(None, max_length=500)
    onset: date | None = None
    status: str | None = Field(None, pattern=STATUS_PATTERN)
    notes: str | None = Field(None, max_length=2000)


class AllergyResponse(BaseModel):
    id: str
    patient_id: str
    substance: str
    category: str
    criticality: str
    severity: str
    reaction: str
    onset: date | None
    status: str
    notes: str
    recorded_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AllergyListResponse(BaseModel):
    allergies: list[AllergyResponse]
    total: int


class AllergyAlert(BaseModel):
    allergy_id: str
    substance: str
    severity: str
    criticality: str
    reaction: str
