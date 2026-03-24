import json
import logging
from datetime import date, datetime, time, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery
from app.config import settings
from app.models.medication import MedicationReminderModel

logger = logging.getLogger(__name__)


def get_session():
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


@celery.task(name="app.tasks.reminders.check_and_send_reminders")
def check_and_send_reminders() -> dict:
    """Check for medication reminders due now and send notifications."""
    db = get_session()
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
            reminder_times = json.loads(reminder.times)
            for t_str in reminder_times:
                reminder_time = time.fromisoformat(t_str)
                # Check if within 5-minute window
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


@celery.task(name="app.tasks.reminders.send_reminder_notification")
def send_reminder_notification(
    reminder_id: str,
    patient_id: str,
    medication_name: str,
    dosage: str,
    instructions: str,
) -> dict:
    """Send a medication reminder notification to a patient.

    In production, this would integrate with SMS (Twilio), push notifications,
    or email. For now, it logs the reminder and returns the notification payload.
    """
    notification = {
        "type": "medication_reminder",
        "reminder_id": reminder_id,
        "patient_id": patient_id,
        "title": f"Time to take {medication_name}",
        "body": f"Take {dosage} of {medication_name}. {instructions}".strip(),
        "delivered": True,
    }
    logger.info("Medication reminder sent: %s %s for patient %s", medication_name, dosage, patient_id)
    return notification


@celery.task(name="app.tasks.reminders.expire_old_reminders")
def expire_old_reminders() -> dict:
    """Mark reminders past their end date as completed."""
    db = get_session()
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
