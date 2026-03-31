from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientHistoryResponse,
    PatientListResponse,
    PatientResponse,
    PatientSelfCreate,
    PatientUpdate,
)
from app.services.audit_logger import log_action
from app.services.patient_service import get_patient_history as get_history
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=201)
def create_patient(
    body: PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Patient:
    """Register a new patient. Requires nurse, doctor, or admin role."""
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    log_action(
        db,
        action="create",
        resource_type="patient",
        resource_id=patient.id,
        detail=f"Created patient: {patient.full_name}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return patient


@router.get("", response_model=PatientListResponse)
def list_patients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> dict:
    """List all patients with pagination and optional search. Requires nurse, doctor, or admin role."""
    query = db.query(Patient).filter(Patient.is_deleted == False)  # noqa: E712
    if search:
        query = query.filter(Patient.full_name.ilike(f"%{search}%"))
    total = query.count()
    patients = query.order_by(Patient.full_name).offset(offset).limit(limit).all()
    return {"patients": patients, "total": total}


@router.post("/me", response_model=PatientResponse, status_code=201)
def self_register_patient(
    body: PatientSelfCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    """Allow a patient-role user to create their own patient record."""
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patient users can self-register")

    # Check if patient record already exists for this user
    existing = (
        db.query(Patient)
        .filter(
            Patient.user_id == current_user.id,
            Patient.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Patient record already exists")

    patient = Patient(**body.model_dump(), user_id=current_user.id)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    log_action(
        db,
        action="create",
        resource_type="patient",
        resource_id=patient.id,
        detail=f"Patient self-registered: {patient.full_name}",
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return patient


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    """Get a patient by ID. Patients can only view their own record; nurses, doctors, and admins can view any."""
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Patients may only access their own record
    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    log_action(
        db,
        action="read",
        resource_type="patient",
        resource_id=patient_id,
        detail=f"Viewed patient: {patient.full_name}",
        user=current_user,
    )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    request: PatientUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Patient:
    """Update a patient's information. Requires nurse, doctor, or admin role."""
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    log_action(
        db,
        action="update",
        resource_type="patient",
        resource_id=patient_id,
        detail=f"Updated fields: {', '.join(update_data.keys())}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Soft-delete a patient. Requires admin role."""
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_deleted = True
    db.commit()
    log_action(
        db,
        action="delete",
        resource_type="patient",
        resource_id=patient_id,
        detail=f"Soft-deleted patient: {patient.full_name}",
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )


@router.get("/{patient_id}/history", response_model=PatientHistoryResponse)
def get_patient_history(
    patient_id: str,
    record_type: str | None = Query(None, pattern="^(triage|symptom_check|vitals)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientHistoryResponse:
    """Get a patient's history of triage assessments and symptom checks."""
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_deleted == False).first()  # noqa: E712
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Patients may only access their own history
    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return get_history(
        db=db,
        patient_id=patient_id,
        patient_name=patient.full_name,
        record_type=record_type,
        limit=limit,
        offset=offset,
    )
