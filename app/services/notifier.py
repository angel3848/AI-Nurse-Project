import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body_html: str, body_text: str) -> bool:
    """Send an email notification. Returns True if sent, False if skipped/failed."""
    if not settings.notification_enabled:
        logger.info("Notifications disabled — would send to %s: %s", to_email, subject)
        return False

    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP not configured — skipping email to %s", to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info("Email sent to %s: %s", to_email, subject)
        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        return False


def build_reminder_email(medication_name: str, dosage: str, instructions: str) -> tuple[str, str, str]:
    """Build email subject, HTML body, and text body for a medication reminder."""
    subject = f"Medication Reminder: {medication_name}"

    body_text = f"Time to take your medication!\n\n" f"Medication: {medication_name}\n" f"Dosage: {dosage}\n"
    if instructions:
        body_text += f"Instructions: {instructions}\n"
    body_text += "\nThis is an automated reminder from AI Nurse."

    body_html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 20px;">
        <div style="background: #2563eb; color: white; padding: 16px 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0; font-size: 18px;">AI Nurse - Medication Reminder</h2>
        </div>
        <div style="border: 1px solid #e5e7eb; border-top: none; padding: 20px; border-radius: 0 0 8px 8px;">
            <p style="font-size: 16px; margin-bottom: 16px;">Time to take your medication!</p>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Medication</td>
                    <td style="padding: 8px 0; font-weight: 600;">{medication_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Dosage</td>
                    <td style="padding: 8px 0; font-weight: 600;">{dosage}</td>
                </tr>
                {"<tr><td style='padding: 8px 0; color: #6b7280; font-size: 14px;'>Instructions</td><td style='padding: 8px 0;'>" + instructions + "</td></tr>" if instructions else ""}
            </table>
            <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
                This is an automated reminder from AI Nurse. Please take your medication as prescribed.
            </p>
        </div>
    </div>
    """

    return subject, body_html, body_text
