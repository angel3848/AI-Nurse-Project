from datetime import date, time, timedelta

from app.models.patient import Patient
from app.schemas.medication import MedicationReminderCreate, MedicationReminderUpdate
from app.services.medication_scheduler import (
    cancel_reminder,
    check_expired_reminders,
    create_reminder,
    get_patient_medications,
    get_reminder,
    update_reminder,
)


def _make_patient(db) -> Patient:
    patient = Patient(full_name="Test Patient", date_of_birth=date(1990, 1, 1), gender="female")
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _create(db, patient_id: str, **overrides) -> str:
    request = MedicationReminderCreate(
        patient_id=patient_id,
        medication_name=overrides.get("medication_name", "Ibuprofen"),
        dosage=overrides.get("dosage", "200mg"),
        frequency=overrides.get("frequency", "twice_daily"),
        times=overrides.get("times", [time(8, 0), time(20, 0)]),
        start_date=overrides.get("start_date", date(2026, 1, 1)),
        end_date=overrides.get("end_date", date(2026, 12, 31)),
        instructions=overrides.get("instructions", ""),
    )
    return create_reminder(db, request).id


class TestUpdateReminder:
    def test_update_dosage(self, db):
        patient = _make_patient(db)
        reminder_id = _create(db, patient.id)
        result = update_reminder(db, reminder_id, MedicationReminderUpdate(dosage="400mg"))
        assert result is not None
        assert result.dosage == "400mg"

    def test_update_times_converts_to_strings(self, db):
        patient = _make_patient(db)
        reminder_id = _create(db, patient.id)
        result = update_reminder(db, reminder_id, MedicationReminderUpdate(times=[time(9, 30)]))
        assert result is not None
        assert result.times == [time(9, 30)]

    def test_update_multiple_fields(self, db):
        patient = _make_patient(db)
        reminder_id = _create(db, patient.id)
        result = update_reminder(
            db,
            reminder_id,
            MedicationReminderUpdate(dosage="500mg", frequency="once_daily", times=[time(12, 0)], instructions="With food"),
        )
        assert result is not None
        assert result.dosage == "500mg"
        assert result.frequency == "once_daily"
        assert result.instructions == "With food"

    def test_update_nonexistent_returns_none(self, db):
        result = update_reminder(db, "nonexistent", MedicationReminderUpdate(dosage="500mg"))
        assert result is None

    def test_update_cancelled_reminder_returns_none(self, db):
        patient = _make_patient(db)
        reminder_id = _create(db, patient.id)
        cancel_reminder(db, reminder_id)
        result = update_reminder(db, reminder_id, MedicationReminderUpdate(dosage="500mg"))
        assert result is None

    def test_update_preserves_unset_fields(self, db):
        patient = _make_patient(db)
        reminder_id = _create(db, patient.id, dosage="100mg", instructions="With water")
        update_reminder(db, reminder_id, MedicationReminderUpdate(dosage="200mg"))
        fetched = get_reminder(db, reminder_id)
        assert fetched is not None
        assert fetched.instructions == "With water"


class TestCheckExpiredReminders:
    def test_marks_past_end_date_as_completed(self, db):
        patient = _make_patient(db)
        yesterday = date.today() - timedelta(days=1)
        reminder_id = _create(db, patient.id, start_date=yesterday - timedelta(days=30), end_date=yesterday)
        count = check_expired_reminders(db)
        assert count >= 1
        fetched = get_reminder(db, reminder_id)
        assert fetched is not None
        assert fetched.status == "completed"

    def test_does_not_expire_active_reminders(self, db):
        patient = _make_patient(db)
        future = date.today() + timedelta(days=30)
        reminder_id = _create(db, patient.id, end_date=future)
        check_expired_reminders(db)
        fetched = get_reminder(db, reminder_id)
        assert fetched is not None
        assert fetched.status == "active"

    def test_returns_count_of_expired(self, db):
        patient = _make_patient(db)
        yesterday = date.today() - timedelta(days=1)
        _create(db, patient.id, start_date=yesterday - timedelta(days=30), end_date=yesterday)
        _create(db, patient.id, start_date=yesterday - timedelta(days=30), end_date=yesterday)
        future = date.today() + timedelta(days=30)
        _create(db, patient.id, end_date=future)
        count = check_expired_reminders(db)
        assert count == 2

    def test_no_expired_returns_zero(self, db):
        patient = _make_patient(db)
        future = date.today() + timedelta(days=30)
        _create(db, patient.id, end_date=future)
        assert check_expired_reminders(db) == 0

    def test_ignores_already_completed(self, db):
        patient = _make_patient(db)
        yesterday = date.today() - timedelta(days=1)
        _create(db, patient.id, start_date=yesterday - timedelta(days=30), end_date=yesterday)
        check_expired_reminders(db)
        assert check_expired_reminders(db) == 0


class TestGetPatientMedications:
    def test_returns_all_for_patient(self, db):
        patient = _make_patient(db)
        _create(db, patient.id, medication_name="A")
        _create(db, patient.id, medication_name="B")
        result = get_patient_medications(db, patient.id)
        assert len(result) == 2

    def test_empty_for_patient_with_no_meds(self, db):
        patient = _make_patient(db)
        assert get_patient_medications(db, patient.id) == []
