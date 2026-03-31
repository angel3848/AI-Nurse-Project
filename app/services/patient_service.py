"""Service layer for patient history assembly.

Handles SQL-level pagination and HistoryRecord construction,
keeping the router thin (auth + validation only).
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.triage import SymptomCheckRecord, TriageRecord
from app.models.vitals import VitalsRecord
from app.schemas.patient import HistoryRecord, PatientHistoryResponse


def _build_triage_record(t: TriageRecord) -> HistoryRecord:
    return HistoryRecord(
        id=t.id,
        record_type="triage",
        summary=f"Level {t.priority_level} ({t.priority_label}) — {t.chief_complaint}",
        details={
            "priority_level": t.priority_level,
            "priority_label": t.priority_label,
            "chief_complaint": t.chief_complaint,
            "symptoms": t.symptoms,
            "pain_scale": t.pain_scale,
            "flags": t.flags,
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
    )


def _build_symptom_record(s: SymptomCheckRecord) -> HistoryRecord:
    conditions = s.conditions_found
    top_condition = conditions[0]["condition"] if conditions else "No match"
    return HistoryRecord(
        id=s.id,
        record_type="symptom_check",
        summary=f"{s.urgency.capitalize()} urgency — {top_condition}",
        details={
            "symptoms": s.symptoms,
            "duration_days": s.duration_days,
            "severity": s.severity,
            "urgency": s.urgency,
            "conditions_found": conditions,
            "recommended_action": s.recommended_action,
        },
        created_at=s.created_at,
    )


def _build_vitals_record(v: VitalsRecord) -> HistoryRecord:
    return HistoryRecord(
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
    )


def get_patient_history(
    db: Session,
    patient_id: str,
    patient_name: str,
    record_type: str | None,
    limit: int,
    offset: int,
) -> PatientHistoryResponse:
    """Assemble paginated patient history from triage, symptom, and vitals tables.

    When a record_type filter is provided, only that single table is queried
    with SQL-level LIMIT/OFFSET.  When no filter is provided, each table is
    queried with ORDER BY + LIMIT (offset+limit) to cap memory, then the
    results are merged, sorted, and sliced in Python.
    """

    # --- Single-table fast path (SQL-level pagination) ---
    if record_type == "triage":
        total = db.query(func.count(TriageRecord.id)).filter(TriageRecord.patient_id == patient_id).scalar()
        rows = (
            db.query(TriageRecord)
            .filter(TriageRecord.patient_id == patient_id)
            .order_by(TriageRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        records = [_build_triage_record(r) for r in rows]
        return PatientHistoryResponse(
            patient_id=patient_id,
            patient_name=patient_name,
            records=records,
            total=total,
        )

    if record_type == "symptom_check":
        total = db.query(func.count(SymptomCheckRecord.id)).filter(SymptomCheckRecord.patient_id == patient_id).scalar()
        rows = (
            db.query(SymptomCheckRecord)
            .filter(SymptomCheckRecord.patient_id == patient_id)
            .order_by(SymptomCheckRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        records = [_build_symptom_record(r) for r in rows]
        return PatientHistoryResponse(
            patient_id=patient_id,
            patient_name=patient_name,
            records=records,
            total=total,
        )

    if record_type == "vitals":
        total = db.query(func.count(VitalsRecord.id)).filter(VitalsRecord.patient_id == patient_id).scalar()
        rows = (
            db.query(VitalsRecord)
            .filter(VitalsRecord.patient_id == patient_id)
            .order_by(VitalsRecord.recorded_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        records = [_build_vitals_record(r) for r in rows]
        return PatientHistoryResponse(
            patient_id=patient_id,
            patient_name=patient_name,
            records=records,
            total=total,
        )

    # --- No filter: query all three tables with capped SQL LIMIT ---
    # Cap each sub-query to (offset + limit) rows so total memory is bounded
    # to 3 * (offset + limit) instead of unbounded.
    sql_cap = offset + limit

    triage_total = db.query(func.count(TriageRecord.id)).filter(TriageRecord.patient_id == patient_id).scalar()
    triage_rows = (
        db.query(TriageRecord)
        .filter(TriageRecord.patient_id == patient_id)
        .order_by(TriageRecord.created_at.desc())
        .limit(sql_cap)
        .all()
    )

    symptom_total = (
        db.query(func.count(SymptomCheckRecord.id)).filter(SymptomCheckRecord.patient_id == patient_id).scalar()
    )
    symptom_rows = (
        db.query(SymptomCheckRecord)
        .filter(SymptomCheckRecord.patient_id == patient_id)
        .order_by(SymptomCheckRecord.created_at.desc())
        .limit(sql_cap)
        .all()
    )

    vitals_total = db.query(func.count(VitalsRecord.id)).filter(VitalsRecord.patient_id == patient_id).scalar()
    vitals_rows = (
        db.query(VitalsRecord)
        .filter(VitalsRecord.patient_id == patient_id)
        .order_by(VitalsRecord.recorded_at.desc())
        .limit(sql_cap)
        .all()
    )

    total = triage_total + symptom_total + vitals_total

    all_records: list[HistoryRecord] = []
    all_records.extend(_build_triage_record(r) for r in triage_rows)
    all_records.extend(_build_symptom_record(r) for r in symptom_rows)
    all_records.extend(_build_vitals_record(r) for r in vitals_rows)

    all_records.sort(key=lambda r: r.created_at, reverse=True)
    page = all_records[offset : offset + limit]

    return PatientHistoryResponse(
        patient_id=patient_id,
        patient_name=patient_name,
        records=page,
        total=total,
    )
