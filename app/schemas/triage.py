from pydantic import BaseModel, Field


class Vitals(BaseModel):
    heart_rate: int = Field(..., gt=0, le=300, description="Beats per minute")
    blood_pressure_systolic: int = Field(..., gt=0, le=350)
    blood_pressure_diastolic: int = Field(..., gt=0, le=250)
    temperature_c: float = Field(..., gt=25.0, le=45.0)
    respiratory_rate: int = Field(..., gt=0, le=80)
    oxygen_saturation: int = Field(..., gt=0, le=100, description="SpO2 percentage")


class TriageRequest(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=200)
    chief_complaint: str = Field(..., min_length=1, max_length=1000)
    symptoms: list[str] = Field(..., min_length=1)
    symptom_duration: str = Field(..., min_length=1, max_length=200)
    vitals: Vitals
    pain_scale: int = Field(..., ge=0, le=10)
    age: int = Field(..., gt=0, le=150)
    notes: str = Field("", max_length=2000)


class TriageResponse(BaseModel):
    patient_name: str
    priority_level: int = Field(..., ge=1, le=5)
    priority_label: str
    priority_color: str
    recommended_action: str
    flags: list[str]
    vitals_summary: dict[str, str]
