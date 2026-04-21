from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.allergy import Allergy
from app.models.patient import Patient
from app.models.user import User
from app.schemas.allergy import (
    AllergyCreate,
    AllergyResponse,
    AllergyUpdate,
)
from app.services import allergy_service
from app.services.audit_logger import log_action
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/allergies", tags=["Allergies"])


def _patient_or_404(db: Session, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _check_patient_access(patient: Patient, current_user: User) -> None:
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("", response_model=AllergyResponse, status_code=201)
def create_allergy_endpoint(
    body: AllergyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Allergy:
    """Record a new allergy for a patient. Requires nurse, doctor, or admin role."""
    _patient_or_404(db, body.patient_id)

    allergy = allergy_service.create_allergy(
        db,
        patient_id=body.patient_id,
        substance=body.substance,
        category=body.category,
        criticality=body.criticality,
        severity=body.severity,
        reaction=body.reaction,
        onset=body.onset,
        notes=body.notes,
        recorded_by=current_user,
    )
    log_action(
        db,
        action="create",
        resource_type="allergy",
        resource_id=allergy.id,
        detail=f"Recorded {body.severity} {body.category} allergy to {body.substance}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return allergy


@router.get("", response_model=dict)
def list_allergies_endpoint(
    patient_id: str = Query(..., min_length=1),
    include_inactive: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List allergies for a patient. Patients see own; staff can see any."""
    patient = _patient_or_404(db, patient_id)
    _check_patient_access(patient, current_user)

    allergies, total = allergy_service.list_allergies(
        db,
        patient_id=patient_id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return {"allergies": allergies, "total": total}


@router.patch("/{allergy_id}", response_model=AllergyResponse)
def update_allergy_endpoint(
    allergy_id: str,
    body: AllergyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Allergy:
    """Update an allergy record."""
    updates = body.model_dump(exclude_unset=True)
    allergy = allergy_service.update_allergy(db, allergy_id, updates)
    log_action(
        db,
        action="update",
        resource_type="allergy",
        resource_id=allergy_id,
        detail=f"Updated fields: {', '.join(updates.keys())}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return allergy


@router.delete("/{allergy_id}", response_model=AllergyResponse)
def deactivate_allergy_endpoint(
    allergy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Allergy:
    """Soft-delete an allergy by setting status=inactive."""
    allergy = allergy_service.deactivate_allergy(db, allergy_id)
    log_action(
        db,
        action="deactivate",
        resource_type="allergy",
        resource_id=allergy_id,
        detail=f"Deactivated allergy to {allergy.substance}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return allergy
