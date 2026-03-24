from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.models.vitals import VitalsRecord
from app.schemas.metrics import (
    BMIRequest,
    BMIResponse,
    VitalsHistoryResponse,
    VitalsRecordRequest,
    VitalsRecordResponse,
)
from app.services.audit_logger import log_action
from app.services.bmi_calculator import assess_bmi
from app.services.vitals_assessor import assess_all_vitals
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/metrics", tags=["Health Metrics"])


@router.post("/bmi", response_model=BMIResponse)
def calculate_bmi(request: BMIRequest) -> BMIResponse:
    """Calculate BMI from height and weight, returning category and interpretation."""
    return assess_bmi(request)


@router.post("/vitals", response_model=VitalsRecordResponse, status_code=201)
def record_vitals(
    request: VitalsRecordRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> VitalsRecordResponse:
    """Record patient vital signs. Requires nurse or doctor role."""
    patient = db.query(Patient).filter(Patient.id == request.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    readings, alerts = assess_all_vitals(
        heart_rate=request.heart_rate,
        bp_systolic=request.blood_pressure_systolic,
        bp_diastolic=request.blood_pressure_diastolic,
        temperature_c=request.temperature_c,
        respiratory_rate=request.respiratory_rate,
        oxygen_saturation=request.oxygen_saturation,
        blood_glucose_mg_dl=request.blood_glucose_mg_dl,
    )

    record = VitalsRecord(
        patient_id=request.patient_id,
        recorded_by=current_user.id,
        heart_rate=request.heart_rate,
        bp_systolic=request.blood_pressure_systolic,
        bp_diastolic=request.blood_pressure_diastolic,
        temperature_c=request.temperature_c,
        respiratory_rate=request.respiratory_rate,
        oxygen_saturation=request.oxygen_saturation,
        blood_glucose_mg_dl=request.blood_glucose_mg_dl,
        notes=request.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    log_action(
        db,
        action="create",
        resource_type="vitals",
        resource_id=record.id,
        detail=f"Recorded vitals for patient {request.patient_id}" + (f" — alerts: {', '.join(alerts)}" if alerts else ""),
        user=current_user,
        ip_address=http_request.client.host if http_request.client else None,
    )

    return VitalsRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        readings=readings,
        alerts=alerts,
        notes=record.notes,
        recorded_by=current_user.id,
        recorded_at=record.recorded_at,
    )


@router.get("/vitals/{patient_id}", response_model=VitalsHistoryResponse)
def get_vitals_history(
    patient_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VitalsHistoryResponse:
    """Get vitals history for a patient. Requires authentication."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = db.query(VitalsRecord).filter(VitalsRecord.patient_id == patient_id)
    total = query.count()
    records = query.order_by(VitalsRecord.recorded_at.desc()).offset(offset).limit(limit).all()

    responses = []
    for r in records:
        readings, alerts = assess_all_vitals(
            heart_rate=r.heart_rate,
            bp_systolic=r.bp_systolic,
            bp_diastolic=r.bp_diastolic,
            temperature_c=r.temperature_c,
            respiratory_rate=r.respiratory_rate,
            oxygen_saturation=r.oxygen_saturation,
            blood_glucose_mg_dl=r.blood_glucose_mg_dl,
        )
        responses.append(VitalsRecordResponse(
            id=r.id,
            patient_id=r.patient_id,
            readings=readings,
            alerts=alerts,
            notes=r.notes,
            recorded_by=r.recorded_by,
            recorded_at=r.recorded_at,
        ))

    log_action(
        db,
        action="read",
        resource_type="vitals",
        resource_id=patient_id,
        detail=f"Viewed vitals history ({total} records)",
        user=current_user,
    )

    return VitalsHistoryResponse(patient_id=patient_id, records=responses, total=total)
