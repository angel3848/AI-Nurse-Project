from datetime import datetime

from pydantic import BaseModel, Field


class BMIRequest(BaseModel):
    height_cm: float = Field(..., gt=0, le=300, description="Height in centimeters")
    weight_kg: float = Field(..., gt=0, le=700, description="Weight in kilograms")


class HealthyWeightRange(BaseModel):
    min_kg: float
    max_kg: float


class BMIResponse(BaseModel):
    bmi: float
    category: str
    healthy_weight_range: HealthyWeightRange
    interpretation: str


class VitalsRecordRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    heart_rate: int = Field(..., gt=0, le=300)
    blood_pressure_systolic: int = Field(..., gt=0, le=350)
    blood_pressure_diastolic: int = Field(..., gt=0, le=250)
    temperature_c: float = Field(..., gt=25.0, le=45.0)
    respiratory_rate: int = Field(..., gt=0, le=80)
    oxygen_saturation: int = Field(..., gt=0, le=100)
    blood_glucose_mg_dl: int | None = Field(None, gt=0, le=1000)
    notes: str = Field("", max_length=500)


class VitalReading(BaseModel):
    value: float | int | str
    status: str


class VitalsRecordResponse(BaseModel):
    id: str
    patient_id: str
    readings: dict[str, VitalReading]
    alerts: list[str]
    notes: str
    recorded_by: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class VitalsHistoryResponse(BaseModel):
    patient_id: str
    records: list[VitalsRecordResponse]
    total: int
