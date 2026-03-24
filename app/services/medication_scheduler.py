import uuid
from datetime import date

from app.schemas.medication import (
    MedicationListResponse,
    MedicationReminder,
    MedicationReminderCreate,
)

# In-memory store — will be replaced with database in future
_reminders: dict[str, MedicationReminder] = {}


def create_reminder(request: MedicationReminderCreate) -> MedicationReminder:
    """Create a new medication reminder."""
    if request.end_date < request.start_date:
        raise ValueError("end_date must be on or after start_date")

    reminder_id = str(uuid.uuid4())
    reminder = MedicationReminder(
        id=reminder_id,
        patient_name=request.patient_name,
        medication_name=request.medication_name,
        dosage=request.dosage,
        frequency=request.frequency,
        times=request.times,
        start_date=request.start_date,
        end_date=request.end_date,
        instructions=request.instructions,
        status="active",
    )
    _reminders[reminder_id] = reminder
    return reminder


def get_reminder(reminder_id: str) -> MedicationReminder | None:
    """Get a single reminder by ID."""
    return _reminders.get(reminder_id)


def get_patient_medications(patient_name: str) -> MedicationListResponse:
    """Get all medications for a patient."""
    meds = [r for r in _reminders.values() if r.patient_name == patient_name]
    return MedicationListResponse(
        patient_name=patient_name,
        medications=meds,
        total=len(meds),
    )


def cancel_reminder(reminder_id: str) -> MedicationReminder | None:
    """Cancel a medication reminder."""
    reminder = _reminders.get(reminder_id)
    if reminder is None:
        return None

    updated = reminder.model_copy(update={"status": "cancelled"})
    _reminders[reminder_id] = updated
    return updated


def check_expired_reminders() -> int:
    """Mark reminders past their end_date as completed. Returns count updated."""
    today = date.today()
    count = 0
    for rid, reminder in _reminders.items():
        if reminder.status == "active" and reminder.end_date < today:
            _reminders[rid] = reminder.model_copy(update={"status": "completed"})
            count += 1
    return count


def clear_all_reminders() -> None:
    """Clear all reminders. Used for testing."""
    _reminders.clear()
