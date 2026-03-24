from app.schemas.metrics import VitalReading


def assess_reading(name: str, value: float | int) -> VitalReading:
    """Assess a single vital sign reading and return its status."""
    ranges = {
        "heart_rate": [(60, 100, "normal"), (50, 60, "low"), (100, 130, "elevated"), (0, 50, "critical_low"), (130, 300, "critical_high")],
        "bp_systolic": [(90, 120, "normal"), (120, 140, "elevated"), (140, 180, "high"), (180, 350, "critical_high"), (0, 90, "low")],
        "bp_diastolic": [(60, 80, "normal"), (80, 90, "elevated"), (90, 120, "high"), (120, 250, "critical_high"), (0, 60, "low")],
        "temperature_c": [(36.1, 37.2, "normal"), (37.2, 38.0, "low_grade_fever"), (38.0, 39.0, "fever"), (39.0, 45.0, "high_fever"), (25.0, 36.1, "hypothermia")],
        "respiratory_rate": [(12, 20, "normal"), (20, 30, "elevated"), (30, 80, "critical_high"), (0, 12, "low")],
        "oxygen_saturation": [(95, 100, "normal"), (90, 95, "low"), (0, 90, "critical_low")],
        "blood_glucose_mg_dl": [(70, 100, "normal"), (100, 126, "elevated"), (126, 1000, "high"), (0, 70, "low")],
    }

    for low, high, status in ranges.get(name, []):
        if low <= value < high:
            return VitalReading(value=value, status=status)

    return VitalReading(value=value, status="unknown")


def get_alerts(readings: dict[str, VitalReading]) -> list[str]:
    """Generate alert messages for abnormal readings."""
    alerts = []
    alert_messages = {
        "critical_low": "{name} is critically low ({value})",
        "critical_high": "{name} is critically high ({value})",
        "high_fever": "High fever detected ({value}°C)",
        "hypothermia": "Hypothermia detected ({value}°C)",
        "high": "{name} is high ({value})",
        "low": "{name} is low ({value})",
    }

    for name, reading in readings.items():
        if reading.status in alert_messages:
            display_name = name.replace("_", " ").replace("bp ", "BP ").title()
            alerts.append(alert_messages[reading.status].format(name=display_name, value=reading.value))

    return alerts


def assess_all_vitals(
    heart_rate: int,
    bp_systolic: int,
    bp_diastolic: int,
    temperature_c: float,
    respiratory_rate: int,
    oxygen_saturation: int,
    blood_glucose_mg_dl: int | None = None,
) -> tuple[dict[str, VitalReading], list[str]]:
    """Assess all vitals and return readings with alerts."""
    readings = {
        "heart_rate": assess_reading("heart_rate", heart_rate),
        "blood_pressure_systolic": assess_reading("bp_systolic", bp_systolic),
        "blood_pressure_diastolic": assess_reading("bp_diastolic", bp_diastolic),
        "temperature_c": assess_reading("temperature_c", temperature_c),
        "respiratory_rate": assess_reading("respiratory_rate", respiratory_rate),
        "oxygen_saturation": assess_reading("oxygen_saturation", oxygen_saturation),
    }

    if blood_glucose_mg_dl is not None:
        readings["blood_glucose_mg_dl"] = assess_reading("blood_glucose_mg_dl", blood_glucose_mg_dl)

    alerts = get_alerts(readings)
    return readings, alerts
