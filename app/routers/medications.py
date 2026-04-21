from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.allergy import AllergyAlert
from app.schemas.medication import (
    MedicationListResponse,
    MedicationReminderCreate,
    MedicationReminderResponse,
    MedicationReminderUpdate,
)
from app.services import allergy_service
from app.services.audit_logger import log_action
from app.services.medication_scheduler import (
    cancel_reminder,
    create_reminder,
    get_patient_medications,
    get_reminder,
    update_reminder,
)
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/medications", tags=["Medications"])


@router.post("/reminders", response_model=MedicationReminderResponse, status_code=201)
def create_medication_reminder(
    body: MedicationReminderCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> MedicationReminderResponse:
    """Create a medication reminder. Requires nurse or doctor role.

    Warns (does not block) if the medication name matches any recorded active
    allergy for the patient. Severe-criticality matches are audit-logged.
    """
    try:
        reminder = create_reminder(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    matches = allergy_service.check_medication_contraindications(
        db, patient_id=body.patient_id, medication_name=body.medication_name
    )
    if matches:
        reminder.allergy_alerts = [
            AllergyAlert(
                allergy_id=a.id,
                substance=a.substance,
                severity=a.severity,
                criticality=a.criticality,
                reaction=a.reaction,
            )
            for a in matches
        ]
        severe = [a for a in matches if a.criticality == "high" or a.severity == "severe"]
        if severe:
            log_action(
                db,
                action="create",
                resource_type="medication_reminder",
                resource_id=reminder.id,
                detail=(
                    f"WARNING: prescribed {body.medication_name} to patient {body.patient_id} "
                    f"with active severe/high-criticality allergies: "
                    f"{', '.join(a.substance for a in severe)}"
                ),
                user=current_user,
                ip_address=http_request.client.host if http_request.client else None,
            )
    return reminder


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


@router.put("/reminders/{reminder_id}", response_model=MedicationReminderResponse)
def update_medication_reminder(
    reminder_id: str,
    request: MedicationReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> MedicationReminderResponse:
    """Update an active medication reminder. Requires nurse or doctor role."""
    reminder = update_reminder(db, reminder_id, request)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Active reminder not found")
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
