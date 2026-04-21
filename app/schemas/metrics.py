from datetime import datetime

from pydantic import BaseModel, Field


class BMIRequest(BaseModel):
    height_cm: float | None = Field(None, gt=0, le=300, description="Height in centimeters")
    weight_kg: float | None = Field(None, gt=0, le=700, description="Weight in kilograms")
    height_ft: float | None = Field(None, gt=0, le=9, description="Height feet (imperial)")
    height_in: float | None = Field(None, ge=0, lt=12, description="Height inches (imperial)")
    weight_lbs: float | None = Field(None, gt=0, le=1500, description="Weight in pounds (imperial)")
    unit_system: str = Field("metric", pattern="^(metric|imperial)$", description="Unit system: metric or imperial")


class HealthyWeightRange(BaseModel):
    min_kg: float
    max_kg: float
    min_lbs: float | None = None
    max_lbs: float | None = None


class BMIResponse(BaseModel):
    bmi: float
    category: str
    healthy_weight_range: HealthyWeightRange
    interpretation: str
    unit_system: str = "metric"


class VitalsRecordRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    encounter_id: str | None = Field(None, description="Optional encounter to attach this vitals record to")
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


class VitalsTrendPoint(BaseModel):
    recorded_at: datetime
    value: float | int


class VitalsTrendResponse(BaseModel):
    patient_id: str
    vital: str
    unit: str
    days: int
    points: list[VitalsTrendPoint]
    count: int
