from datetime import date, time

from sqlalchemy.orm import Session

from app.models.medication import MedicationReminderModel
from app.schemas.medication import MedicationReminderCreate, MedicationReminderResponse, MedicationReminderUpdate


def _model_to_response(model: MedicationReminderModel) -> MedicationReminderResponse:
    return MedicationReminderResponse(
        id=model.id,
        patient_id=model.patient_id,
        medication_name=model.medication_name,
        dosage=model.dosage,
        frequency=model.frequency,
        times=[time.fromisoformat(t) for t in model.times],
        start_date=model.start_date,
        end_date=model.end_date,
        instructions=model.instructions,
        status=model.status,
    )


def create_reminder(db: Session, request: MedicationReminderCreate) -> MedicationReminderResponse:
    if request.end_date < request.start_date:
        raise ValueError("end_date must be on or after start_date")

    reminder = MedicationReminderModel(
        patient_id=request.patient_id,
        medication_name=request.medication_name,
        dosage=request.dosage,
        frequency=request.frequency,
        times=[t.isoformat() for t in request.times],
        start_date=request.start_date,
        end_date=request.end_date,
        instructions=request.instructions,
        status="active",
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return _model_to_response(reminder)


def get_reminder(db: Session, reminder_id: str) -> MedicationReminderResponse | None:
    model = db.query(MedicationReminderModel).filter(MedicationReminderModel.id == reminder_id).first()
    if model is None:
        return None
    return _model_to_response(model)


def get_patient_medications(db: Session, patient_id: str) -> list[MedicationReminderResponse]:
    models = db.query(MedicationReminderModel).filter(MedicationReminderModel.patient_id == patient_id).all()
    return [_model_to_response(m) for m in models]


def update_reminder(
    db: Session, reminder_id: str, update: MedicationReminderUpdate
) -> MedicationReminderResponse | None:
    model = (
        db.query(MedicationReminderModel)
        .filter(MedicationReminderModel.id == reminder_id, MedicationReminderModel.status == "active")
        .first()
    )
    if model is None:
        return None

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "times":
            setattr(model, field, [t.isoformat() for t in value])
        else:
            setattr(model, field, value)

    db.commit()
    db.refresh(model)
    return _model_to_response(model)


def cancel_reminder(db: Session, reminder_id: str) -> MedicationReminderResponse | None:
    model = db.query(MedicationReminderModel).filter(MedicationReminderModel.id == reminder_id).first()
    if model is None:
        return None
    model.status = "cancelled"
    db.commit()
    db.refresh(model)
    return _model_to_response(model)


def check_expired_reminders(db: Session) -> int:
    today = date.today()
    expired = (
        db.query(MedicationReminderModel)
        .filter(MedicationReminderModel.status == "active", MedicationReminderModel.end_date < today)
        .all()
    )
    for model in expired:
        model.status = "completed"
    db.commit()
    return len(expired)
