from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=201)
def create_patient(
    request: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Patient:
    """Register a new patient. Requires nurse, doctor, or admin role."""
    patient = Patient(**request.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=PatientListResponse)
def list_patients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> dict:
    """List all patients with pagination. Requires nurse, doctor, or admin role."""
    total = db.query(Patient).count()
    patients = db.query(Patient).offset(offset).limit(limit).all()
    return {"patients": patients, "total": total}


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    """Get a patient by ID. Requires authentication."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    request: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Patient:
    """Update a patient's information. Requires nurse, doctor, or admin role."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Delete a patient. Requires admin role."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
