import logging
from datetime import date, datetime, time, timezone

from app.celery_app import celery
from app.database import get_standalone_session
from app.models.medication import MedicationReminderModel
from app.models.patient import Patient
from app.models.user import User
from app.services.event_bus import publish_user_event
from app.services.notifier import build_reminder_email, send_email

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.reminders.check_and_send_reminders")
def check_and_send_reminders() -> dict:
    """Check for medication reminders due now and send notifications."""
    db = get_standalone_session()
    try:
        today = date.today()
        now = datetime.now(timezone.utc).time()

        active_reminders = (
            db.query(MedicationReminderModel)
            .filter(
                MedicationReminderModel.status == "active",
                MedicationReminderModel.start_date <= today,
                MedicationReminderModel.end_date >= today,
            )
            .all()
        )

        sent_count = 0
        for reminder in active_reminders:
            reminder_times = reminder.times  # Native JSON list
            for t_str in reminder_times:
                reminder_time = time.fromisoformat(t_str)
                now_minutes = now.hour * 60 + now.minute
                reminder_minutes = reminder_time.hour * 60 + reminder_time.minute
                if 0 <= now_minutes - reminder_minutes < 5:
                    send_reminder_notification.delay(
                        reminder.id,
                        reminder.patient_id,
                        reminder.medication_name,
                        reminder.dosage,
                        reminder.instructions,
                    )
                    sent_count += 1

        logger.info("Checked %d active reminders, dispatched %d notifications", len(active_reminders), sent_count)
        return {"checked": len(active_reminders), "sent": sent_count}
    finally:
        db.close()


@celery.task(name="app.tasks.reminders.send_reminder_notification", bind=True, max_retries=3)
def send_reminder_notification(
    self,
    reminder_id: str,
    patient_id: str,
    medication_name: str,
    dosage: str,
    instructions: str,
) -> dict:
    """Send a medication reminder notification via email."""
    db = get_standalone_session()
    try:
        # Look up patient's associated user email
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            logger.warning("Patient %s not found for reminder %s", patient_id, reminder_id)
            return {"delivered": False, "reason": "patient_not_found"}

        # Use the user_id FK to find the associated user
        user = db.query(User).filter(User.id == patient.user_id).first() if patient.user_id else None
        to_email = user.email if user else None

        subject, body_html, body_text = build_reminder_email(medication_name, dosage, instructions)

        delivered = False
        if to_email:
            delivered = send_email(to_email, subject, body_html, body_text)

        notification = {
            "type": "medication_reminder",
            "reminder_id": reminder_id,
            "patient_id": patient_id,
            "to_email": to_email,
            "title": f"Time to take {medication_name}",
            "body": f"Take {dosage} of {medication_name}. {instructions}".strip(),
            "delivered": delivered,
        }

        if user is not None:
            publish_user_event(user.id, notification)
        logger.info(
            "Medication reminder %s: %s %s for patient %s (email=%s, delivered=%s)",
            reminder_id,
            medication_name,
            dosage,
            patient_id,
            to_email,
            delivered,
        )
        return notification

    except Exception as exc:
        logger.error("Failed to send reminder %s: %s", reminder_id, str(exc))
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery.task(name="app.tasks.reminders.expire_old_reminders")
def expire_old_reminders() -> dict:
    """Mark reminders past their end date as completed."""
    db = get_standalone_session()
    try:
        today = date.today()
        expired = (
            db.query(MedicationReminderModel)
            .filter(
                MedicationReminderModel.status == "active",
                MedicationReminderModel.end_date < today,
            )
            .all()
        )
        for reminder in expired:
            reminder.status = "completed"
        db.commit()
        logger.info("Expired %d reminders", len(expired))
        return {"expired": len(expired)}
    finally:
        db.close()
