from datetime import date, time

from pydantic import BaseModel, Field


class MedicationReminderCreate(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=200)
    medication_name: str = Field(..., min_length=1, max_length=200)
    dosage: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field(..., pattern="^(once_daily|twice_daily|three_times_daily|four_times_daily|as_needed)$")
    times: list[time] = Field(..., min_length=1, max_length=4)
    start_date: date
    end_date: date
    instructions: str = Field("", max_length=500)


class MedicationReminder(BaseModel):
    id: str
    patient_name: str
    medication_name: str
    dosage: str
    frequency: str
    times: list[time]
    start_date: date
    end_date: date
    instructions: str
    status: str


class MedicationListResponse(BaseModel):
    patient_name: str
    medications: list[MedicationReminder]
    total: int
