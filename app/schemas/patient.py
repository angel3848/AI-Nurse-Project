from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    date_of_birth: date
    gender: str = Field(..., pattern="^(male|female|other)$")
    blood_type: str | None = Field(None, max_length=5)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    allergies: str | None = Field(None, max_length=1000)
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)


class PatientUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    blood_type: str | None = Field(None, max_length=5)
    height_cm: float | None = Field(None, gt=0, le=300)
    weight_kg: float | None = Field(None, gt=0, le=700)
    allergies: str | None = Field(None, max_length=1000)
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=20)


class PatientResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: date
    gender: str
    blood_type: str | None
    height_cm: float | None
    weight_kg: float | None
    allergies: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int
