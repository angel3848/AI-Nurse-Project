import logging

import anthropic
from anthropic.types import TextBlock

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a medical triage assistant. Based on the patient's symptoms, "
    "duration, severity, and age, provide a brief clinical analysis. Include: "
    "1) Your assessment of the situation 2) Key considerations "
    "3) Recommended next steps. Keep response under 200 words. "
    "Always include a disclaimer that this is not a medical diagnosis."
)


def analyze_symptoms_with_ai(
    symptoms: list[str],
    duration_days: int,
    severity: str,
    age: int,
    additional_info: str,
    rule_based_results: dict,
) -> str:
    """Send symptom data to Claude for AI-powered clinical analysis."""
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        conditions_summary = ""
        for condition in rule_based_results.get("possible_conditions", []):
            conditions_summary += (
                f"- {condition['condition']} "
                f"(probability: {condition['probability']}, "
                f"category: {condition['category']})\n"
            )

        user_message = (
            f"Patient age: {age}\n"
            f"Symptoms: {', '.join(symptoms)}\n"
            f"Duration: {duration_days} day(s)\n"
            f"Severity: {severity}\n"
            f"Additional info: {additional_info or 'None provided'}\n\n"
            f"Rule-based triage results:\n"
            f"Urgency: {rule_based_results.get('urgency', 'unknown')}\n"
            f"Recommended action: {rule_based_results.get('recommended_action', 'N/A')}\n"
            f"Possible conditions:\n{conditions_summary or 'None matched'}"
        )

        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        for block in message.content:
            if isinstance(block, TextBlock):
                return block.text
        return "AI analysis unavailable."

    except Exception:
        logger.exception("AI symptom analysis failed")
        return "AI analysis unavailable."
