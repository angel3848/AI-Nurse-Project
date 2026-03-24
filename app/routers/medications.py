from fastapi import APIRouter, HTTPException

from app.schemas.medication import (
    MedicationListResponse,
    MedicationReminder,
    MedicationReminderCreate,
)
from app.services.medication_scheduler import (
    cancel_reminder,
    create_reminder,
    get_patient_medications,
    get_reminder,
)

router = APIRouter(prefix="/api/v1/medications", tags=["Medications"])


@router.post("/reminders", response_model=MedicationReminder, status_code=201)
def create_medication_reminder(request: MedicationReminderCreate) -> MedicationReminder:
    """Create a medication reminder for a patient."""
    try:
        return create_reminder(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reminders/{reminder_id}", response_model=MedicationReminder)
def get_medication_reminder(reminder_id: str) -> MedicationReminder:
    """Get a specific medication reminder."""
    reminder = get_reminder(reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.get("/patient/{patient_name}", response_model=MedicationListResponse)
def list_patient_medications(patient_name: str) -> MedicationListResponse:
    """List all medications for a patient."""
    return get_patient_medications(patient_name)


@router.delete("/reminders/{reminder_id}", response_model=MedicationReminder)
def delete_medication_reminder(reminder_id: str) -> MedicationReminder:
    """Cancel a medication reminder."""
    reminder = cancel_reminder(reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder
