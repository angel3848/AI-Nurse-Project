from datetime import datetime

from pydantic import BaseModel, Field

STATUS_PATTERN = "^(planned|in-progress|completed|cancelled)$"
CLASS_PATTERN = "^(emergency|outpatient|inpatient|virtual)$"
DISPOSITION_PATTERN = "^(discharged_home|admitted|transferred|referred|ama|lwbs)$"


class EncounterCreate(BaseModel):
    patient_id: str = Field(..., min_length=1)
    encounter_class: str = Field("emergency", pattern=CLASS_PATTERN)
    reason_code: str = Field("", max_length=500)


class EncounterUpdate(BaseModel):
    status: str | None = Field(None, pattern=STATUS_PATTERN)
    reason_code: str | None = Field(None, max_length=500)


class EncounterClose(BaseModel):
    disposition: str = Field(..., pattern=DISPOSITION_PATTERN)
    disposition_notes: str = Field("", max_length=2000)


class EncounterResponse(BaseModel):
    id: str
    patient_id: str
    status: str
    encounter_class: str
    reason_code: str
    period_start: datetime
    period_end: datetime | None
    disposition: str | None
    disposition_notes: str
    opened_by: str
    closed_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EncounterTriageSummary(BaseModel):
    id: str
    chief_complaint: str
    priority_level: int
    priority_label: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EncounterVitalsSummary(BaseModel):
    id: str
    heart_rate: int
    bp_systolic: int
    bp_diastolic: int
    temperature_c: float
    respiratory_rate: int
    oxygen_saturation: int
    recorded_at: datetime

    model_config = {"from_attributes": True}


class EncounterSymptomCheckSummary(BaseModel):
    id: str
    severity: str
    urgency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EncounterDetailResponse(EncounterResponse):
    triage_records: list[EncounterTriageSummary] = []
    vitals_records: list[EncounterVitalsSummary] = []
    symptom_checks: list[EncounterSymptomCheckSummary] = []


class EncounterListResponse(BaseModel):
    encounters: list[EncounterResponse]
    total: int
