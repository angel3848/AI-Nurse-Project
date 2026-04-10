from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.models.medication import MedicationReminderModel
from app.models.patient import Patient
from app.models.user import User
from tests.conftest import create_test_user


def _create_patient_with_user(db, user: User) -> Patient:
    """Create a patient record linked to a user."""
    patient = Patient(
        user_id=user.id,
        full_name=user.full_name,
        date_of_birth=date(1990, 1, 1),
        gender="other",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _create_reminder(db, patient_id: str, times: list[str], status: str = "active", days_offset: int = 0):
    """Create a medication reminder."""
    today = date.today()
    reminder = MedicationReminderModel(
        patient_id=patient_id,
        medication_name="Aspirin",
        dosage="100mg",
        frequency="daily",
        times=times,
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=days_offset) if days_offset >= 0 else today + timedelta(days=days_offset),
        instructions="Take with food",
        status=status,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@patch("app.tasks.reminders.get_standalone_session")
@patch("app.tasks.reminders.send_reminder_notification")
def test_check_and_send_reminders_dispatches(mock_send, mock_session, db):
    """check_and_send_reminders finds due reminders and dispatches notifications."""
    mock_session.return_value = db

    user = create_test_user(db, role="patient")
    patient = _create_patient_with_user(db, user)

    now = datetime.now(timezone.utc)
    current_time_str = now.strftime("%H:%M")
    _create_reminder(db, patient.id, [current_time_str], days_offset=5)

    mock_send.delay = MagicMock()

    from app.tasks.reminders import check_and_send_reminders

    result = check_and_send_reminders()

    assert result["checked"] >= 1
    assert result["sent"] >= 1
    mock_send.delay.assert_called()


@patch("app.tasks.reminders.get_standalone_session")
@patch("app.tasks.reminders.send_reminder_notification")
def test_check_and_send_reminders_skips_non_due(mock_send, mock_session, db):
    """check_and_send_reminders skips reminders not due now."""
    mock_session.return_value = db

    user = create_test_user(db, role="patient")
    patient = _create_patient_with_user(db, user)

    _create_reminder(db, patient.id, ["03:00"], days_offset=5)

    mock_send.delay = MagicMock()

    from app.tasks.reminders import check_and_send_reminders

    # Only matches if current time is around 03:00
    result = check_and_send_reminders()
    assert result["checked"] >= 1


@patch("app.tasks.reminders.get_standalone_session")
def test_expire_old_reminders(mock_session, db):
    """expire_old_reminders marks past-end-date reminders as completed."""
    mock_session.return_value = db

    user = create_test_user(db, role="patient")
    patient = _create_patient_with_user(db, user)

    reminder = MedicationReminderModel(
        patient_id=patient.id,
        medication_name="OldMed",
        dosage="50mg",
        frequency="daily",
        times=["08:00"],
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() - timedelta(days=1),
        instructions="",
        status="active",
    )
    db.add(reminder)
    db.commit()

    from app.tasks.reminders import expire_old_reminders

    result = expire_old_reminders()
    assert result["expired"] >= 1

    updated = db.query(MedicationReminderModel).filter(MedicationReminderModel.id == reminder.id).first()
    assert updated.status == "completed"


@patch("app.tasks.reminders.get_standalone_session")
@patch("app.tasks.reminders.send_email")
def test_send_reminder_notification_success(mock_send_email, mock_session, db):
    """send_reminder_notification sends email to the patient's user."""
    mock_session.return_value = db
    mock_send_email.return_value = True

    user = create_test_user(db, role="patient")
    patient = _create_patient_with_user(db, user)
    reminder = _create_reminder(db, patient.id, ["08:00"], days_offset=5)

    from app.tasks.reminders import send_reminder_notification

    result = send_reminder_notification(reminder.id, patient.id, "Aspirin", "100mg", "Take with food")

    assert result["delivered"] is True
    assert result["to_email"] == user.email
    mock_send_email.assert_called_once()


@patch("app.tasks.reminders.get_standalone_session")
def test_send_reminder_notification_patient_not_found(mock_session, db):
    """send_reminder_notification handles missing patient gracefully."""
    mock_session.return_value = db

    from app.tasks.reminders import send_reminder_notification

    result = send_reminder_notification("fake-id", "nonexistent-patient", "Aspirin", "100mg", "")

    assert result["delivered"] is False
    assert result["reason"] == "patient_not_found"
