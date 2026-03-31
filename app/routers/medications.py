from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.medication import (
    MedicationListResponse,
    MedicationReminderCreate,
    MedicationReminderResponse,
)
from app.services.medication_scheduler import (
    cancel_reminder,
    create_reminder,
    get_patient_medications,
    get_reminder,
)
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/medications", tags=["Medications"])


@router.post("/reminders", response_model=MedicationReminderResponse, status_code=201)
def create_medication_reminder(
    request: MedicationReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> MedicationReminderResponse:
    """Create a medication reminder. Requires nurse or doctor role."""
    try:
        return create_reminder(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reminders/{reminder_id}", response_model=MedicationReminderResponse)
def get_medication_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicationReminderResponse:
    """Get a specific medication reminder. Requires authentication."""
    reminder = get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.get("/patient/{patient_id}", response_model=MedicationListResponse)
def list_patient_medications(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicationListResponse:
    """List all medications for a patient. Requires authentication."""
    # Patients may only access their own medications
    if current_user.role == "patient":
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    meds = get_patient_medications(db, patient_id)
    return MedicationListResponse(patient_id=patient_id, medications=meds, total=len(meds))


@router.delete("/reminders/{reminder_id}", response_model=MedicationReminderResponse)
def delete_medication_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> MedicationReminderResponse:
    """Cancel a medication reminder. Requires nurse or doctor role."""
    reminder = cancel_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder
