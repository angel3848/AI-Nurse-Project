import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.triage import SymptomCheckRecord, TriageRecord
from app.models.user import User
from app.models.vitals import VitalsRecord
from app.schemas.patient import (
    HistoryRecord,
    PatientCreate,
    PatientHistoryResponse,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.audit_logger import log_action
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=201)
def create_patient(
    request: PatientCreate,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor", "admin")),
) -> Patient:
    """Register a new patient. Requires nurse, doctor, or admin role."""
    patient = Patient(**request.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    log_action(db, action="create", resource_type="patient", resource_id=patient.id,
               detail=f"Created patient: {patient.full_name}", user=current_user,
               ip_address=http_request.client.host if http_request.client else None)
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
    log_action(db, action="read", resource_type="patient", resource_id=patient_id,
               detail=f"Viewed patient: {patient.full_name}", user=current_user)
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
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    log_action(db, action="update", resource_type="patient", resource_id=patient_id,
               detail=f"Updated fields: {', '.join(update_data.keys())}", user=current_user,
               ip_address=http_request.client.host if http_request.client else None)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Delete a patient. Requires admin role."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_name = patient.full_name
    db.delete(patient)
    db.commit()
    log_action(db, action="delete", resource_type="patient", resource_id=patient_id,
               detail=f"Deleted patient: {patient_name}", user=current_user,
               ip_address=http_request.client.host if http_request.client else None)


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
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    records: list[HistoryRecord] = []

    if record_type is None or record_type == "triage":
        triage_records = (
            db.query(TriageRecord)
            .filter(TriageRecord.patient_id == patient_id)
            .order_by(TriageRecord.created_at.desc())
            .all()
        )
        for t in triage_records:
            records.append(HistoryRecord(
                id=t.id,
                record_type="triage",
                summary=f"Level {t.priority_level} ({t.priority_label}) — {t.chief_complaint}",
                details={
                    "priority_level": t.priority_level,
                    "priority_label": t.priority_label,
                    "chief_complaint": t.chief_complaint,
                    "symptoms": json.loads(t.symptoms),
                    "pain_scale": t.pain_scale,
                    "flags": json.loads(t.flags),
                    "recommended_action": t.recommended_action,
                    "vitals": {
                        "heart_rate": t.heart_rate,
                        "blood_pressure": f"{t.bp_systolic}/{t.bp_diastolic}",
                        "temperature_c": t.temperature_c,
                        "respiratory_rate": t.respiratory_rate,
                        "oxygen_saturation": t.oxygen_saturation,
                    },
                },
                created_at=t.created_at,
            ))

    if record_type is None or record_type == "symptom_check":
        symptom_records = (
            db.query(SymptomCheckRecord)
            .filter(SymptomCheckRecord.patient_id == patient_id)
            .order_by(SymptomCheckRecord.created_at.desc())
            .all()
        )
        for s in symptom_records:
            conditions = json.loads(s.conditions_found)
            top_condition = conditions[0]["condition"] if conditions else "No match"
            records.append(HistoryRecord(
                id=s.id,
                record_type="symptom_check",
                summary=f"{s.urgency.capitalize()} urgency — {top_condition}",
                details={
                    "symptoms": json.loads(s.symptoms),
                    "duration_days": s.duration_days,
                    "severity": s.severity,
                    "urgency": s.urgency,
                    "conditions_found": conditions,
                    "recommended_action": s.recommended_action,
                },
                created_at=s.created_at,
            ))

    if record_type is None or record_type == "vitals":
        vitals_records = (
            db.query(VitalsRecord)
            .filter(VitalsRecord.patient_id == patient_id)
            .order_by(VitalsRecord.recorded_at.desc())
            .all()
        )
        for v in vitals_records:
            records.append(HistoryRecord(
                id=v.id,
                record_type="vitals",
                summary=f"Vitals — HR {v.heart_rate}, BP {v.bp_systolic}/{v.bp_diastolic}, SpO2 {v.oxygen_saturation}%",
                details={
                    "heart_rate": v.heart_rate,
                    "blood_pressure": f"{v.bp_systolic}/{v.bp_diastolic}",
                    "temperature_c": v.temperature_c,
                    "respiratory_rate": v.respiratory_rate,
                    "oxygen_saturation": v.oxygen_saturation,
                    "blood_glucose_mg_dl": v.blood_glucose_mg_dl,
                    "notes": v.notes,
                    "recorded_by": v.recorded_by,
                },
                created_at=v.recorded_at,
            ))

    records.sort(key=lambda r: r.created_at, reverse=True)
    total = len(records)
    records = records[offset:offset + limit]

    return PatientHistoryResponse(
        patient_id=patient_id,
        patient_name=patient.full_name,
        records=records,
        total=total,
    )
