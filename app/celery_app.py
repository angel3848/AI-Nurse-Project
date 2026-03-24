from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "ai_nurse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.reminders"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-medication-reminders": {
            "task": "app.tasks.reminders.check_and_send_reminders",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "expire-old-reminders": {
            "task": "app.tasks.reminders.expire_old_reminders",
            "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        },
    },
)
