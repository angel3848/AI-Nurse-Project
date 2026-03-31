from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other)$")
    blood_type: str | None = Field(None, max_length=5)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    allergies: list[str] | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)
    user_id: str | None = Field(None, max_length=36)


class PatientSelfCreate(BaseModel):
    """Schema for patient self-registration (no user_id — set automatically)."""

    full_name: str = Field(..., min_length=1, max_length=200)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other)$")
    blood_type: str | None = Field(None, max_length=5)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    allergies: list[str] | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)


class PatientUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    blood_type: str | None = Field(None, max_length=5)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    allergies: list[str] | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)
    user_id: str | None = Field(None, max_length=36)


class PatientResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: date
    gender: str
    blood_type: str | None
    height_cm: float | None
    weight_kg: float | None
    allergies: list[str] | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    user_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int


class HistoryRecord(BaseModel):
    id: str
    record_type: str
    summary: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientHistoryResponse(BaseModel):
    patient_id: str
    patient_name: str
    records: list[HistoryRecord]
    total: int
