from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.models.vitals import VitalsRecord
from app.schemas.metrics import (
    BMIRequest,
    BMIResponse,
    VitalReading,
    VitalsHistoryResponse,
    VitalsRecordRequest,
    VitalsRecordResponse,
    VitalsTrendPoint,
    VitalsTrendResponse,
)
from app.services import encounter_service
from app.services.audit_logger import log_action
from app.services.bmi_calculator import assess_bmi
from app.services.vitals_assessor import assess_all_vitals
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/metrics", tags=["Health Metrics"])


@router.post("/bmi", response_model=BMIResponse)
def calculate_bmi(request: BMIRequest) -> BMIResponse:
    """Calculate BMI from height and weight. Supports metric (cm/kg) and imperial (ft+in/lbs)."""
    try:
        return assess_bmi(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/vitals", response_model=VitalsRecordResponse, status_code=201)
def record_vitals(
    body: VitalsRecordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nurse", "doctor")),
) -> VitalsRecordResponse:
    """Record patient vital signs. Requires nurse or doctor role."""
    patient = db.query(Patient).filter(Patient.id == body.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if body.encounter_id:
        encounter_service.assert_encounter_open(db, body.encounter_id, body.patient_id)

    readings, alerts = assess_all_vitals(
        heart_rate=body.heart_rate,
        bp_systolic=body.blood_pressure_systolic,
        bp_diastolic=body.blood_pressure_diastolic,
        temperature_c=body.temperature_c,
        respiratory_rate=body.respiratory_rate,
        oxygen_saturation=body.oxygen_saturation,
        blood_glucose_mg_dl=body.blood_glucose_mg_dl,
    )

    assessments_data = {
        "readings": {k: {"value": v.value, "status": v.status} for k, v in readings.items()},
        "alerts": alerts,
    }

    record = VitalsRecord(
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        recorded_by=current_user.id,
        heart_rate=body.heart_rate,
        bp_systolic=body.blood_pressure_systolic,
        bp_diastolic=body.blood_pressure_diastolic,
        temperature_c=body.temperature_c,
        respiratory_rate=body.respiratory_rate,
        oxygen_saturation=body.oxygen_saturation,
        blood_glucose_mg_dl=body.blood_glucose_mg_dl,
        notes=body.notes,
        assessments=assessments_data,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    log_action(
        db,
        action="create",
        resource_type="vitals",
        resource_id=record.id,
        detail=f"Recorded vitals for patient {body.patient_id}" + (f" — alerts: {', '.join(alerts)}" if alerts else ""),
        user=current_user,
        ip_address=request.client.host if request.client else None,
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

    # Patients may only access their own vitals history
    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(VitalsRecord).filter(VitalsRecord.patient_id == patient_id)
    total = query.count()
    records = query.order_by(VitalsRecord.recorded_at.desc()).offset(offset).limit(limit).all()

    responses = []
    for r in records:
        if r.assessments:
            stored = r.assessments
            readings = {k: VitalReading(**v) for k, v in stored["readings"].items()}
            alerts = stored["alerts"]
        else:
            # Fallback for records created before assessments column existed
            readings, alerts = assess_all_vitals(
                heart_rate=r.heart_rate,
                bp_systolic=r.bp_systolic,
                bp_diastolic=r.bp_diastolic,
                temperature_c=r.temperature_c,
                respiratory_rate=r.respiratory_rate,
                oxygen_saturation=r.oxygen_saturation,
                blood_glucose_mg_dl=r.blood_glucose_mg_dl,
            )
        responses.append(
            VitalsRecordResponse(
                id=r.id,
                patient_id=r.patient_id,
                readings=readings,
                alerts=alerts,
                notes=r.notes,
                recorded_by=r.recorded_by,
                recorded_at=r.recorded_at,
            )
        )

    log_action(
        db,
        action="read",
        resource_type="vitals",
        resource_id=patient_id,
        detail=f"Viewed vitals history ({total} records)",
        user=current_user,
    )

    return VitalsHistoryResponse(patient_id=patient_id, records=responses, total=total)


_VITAL_COLUMNS = {
    "heart_rate": (VitalsRecord.heart_rate, "bpm"),
    "bp_systolic": (VitalsRecord.bp_systolic, "mmHg"),
    "bp_diastolic": (VitalsRecord.bp_diastolic, "mmHg"),
    "temperature_c": (VitalsRecord.temperature_c, "°C"),
    "respiratory_rate": (VitalsRecord.respiratory_rate, "breaths/min"),
    "oxygen_saturation": (VitalsRecord.oxygen_saturation, "%"),
    "blood_glucose_mg_dl": (VitalsRecord.blood_glucose_mg_dl, "mg/dL"),
}


@router.get("/vitals/{patient_id}/trend", response_model=VitalsTrendResponse)
def get_vitals_trend(
    patient_id: str,
    vital: str = Query(..., description="Vital to trend"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VitalsTrendResponse:
    """Return time-series for a single vital over a given window (days)."""
    if vital not in _VITAL_COLUMNS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown vital '{vital}'. Valid: {', '.join(_VITAL_COLUMNS)}",
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    column, unit = _VITAL_COLUMNS[vital]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(VitalsRecord.recorded_at, column)
        .filter(VitalsRecord.patient_id == patient_id, VitalsRecord.recorded_at >= cutoff)
        .order_by(VitalsRecord.recorded_at.asc())
        .all()
    )
    points = [VitalsTrendPoint(recorded_at=ts, value=val) for ts, val in rows if val is not None]

    return VitalsTrendResponse(
        patient_id=patient_id, vital=vital, unit=unit, days=days, points=points, count=len(points)
    )
