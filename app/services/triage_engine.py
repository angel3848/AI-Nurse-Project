from app.schemas.triage import TriageRequest, TriageResponse, Vitals

PRIORITY_LABELS = {
    1: ("Resuscitation", "red"),
    2: ("Emergency", "orange"),
    3: ("Urgent", "yellow"),
    4: ("Semi-Urgent", "green"),
    5: ("Non-Urgent", "blue"),
}

HIGH_RISK_SYMPTOMS = {
    1: {"cardiac_arrest", "respiratory_arrest", "unresponsive", "severe_hemorrhage"},
    2: {
        "chest_pain",
        "stroke_symptoms",
        "severe_allergic_reaction",
        "difficulty_breathing",
        "suicidal_ideation",
        "seizure",
    },
    3: {
        "abdominal_pain",
        "moderate_bleeding",
        "high_fever",
        "fracture",
        "dehydration",
        "acute_mental_health",
    },
}


def assess_vitals(vitals: Vitals) -> tuple[int, list[str]]:
    """Evaluate vitals and return (priority_level, flags)."""
    level = 5
    flags: list[str] = []

    # Level 1 — critical vitals
    if vitals.heart_rate < 40 or vitals.heart_rate > 150:
        level = min(level, 1)
        flags.append("critical_heart_rate")
    if vitals.blood_pressure_systolic < 80:
        level = min(level, 1)
        flags.append("critical_low_bp")
    if vitals.oxygen_saturation < 85:
        level = min(level, 1)
        flags.append("critical_low_o2")
    if vitals.respiratory_rate < 8 or vitals.respiratory_rate > 40:
        level = min(level, 1)
        flags.append("critical_respiratory_rate")

    # Level 2 — serious vitals
    if vitals.heart_rate < 50 or vitals.heart_rate > 130:
        level = min(level, 2)
        flags.append("elevated_heart_rate")
    if vitals.blood_pressure_systolic < 90 or vitals.blood_pressure_systolic > 200:
        level = min(level, 2)
        flags.append("abnormal_blood_pressure")
    if vitals.oxygen_saturation < 90:
        level = min(level, 2)
        flags.append("low_o2_sat")
    if vitals.temperature_c > 40.0:
        level = min(level, 2)
        flags.append("hyperthermia")

    # Level 3 — concerning vitals
    if vitals.heart_rate > 100:
        level = min(level, 3)
        flags.append("tachycardia")
    if vitals.blood_pressure_systolic > 160:
        level = min(level, 3)
        flags.append("hypertension")
    if vitals.temperature_c > 38.5:
        level = min(level, 3)
        flags.append("fever")

    return level, list(dict.fromkeys(flags))


def assess_symptoms(symptoms: list[str]) -> tuple[int, list[str]]:
    """Evaluate symptoms against known high-risk patterns."""
    level = 5
    flags: list[str] = []
    symptom_set = {s.lower() for s in symptoms}

    for priority, risk_symptoms in HIGH_RISK_SYMPTOMS.items():
        matched = symptom_set & risk_symptoms
        if matched:
            level = min(level, priority)
            flags.extend(f"symptom_{s}" for s in matched)

    return level, flags


def assess_pain(pain_scale: int) -> tuple[int, list[str]]:
    """Evaluate pain scale."""
    if pain_scale >= 8:
        return 2, ["severe_pain"]
    if pain_scale >= 5:
        return 3, ["moderate_pain"]
    if pain_scale >= 3:
        return 4, ["mild_pain"]
    return 5, []


def apply_age_modifier(level: int, age: int) -> tuple[int, list[str]]:
    """Bump priority for pediatric and geriatric patients."""
    flags: list[str] = []
    if age < 5 and level > 2:
        level = max(level - 1, 2)
        flags.append("pediatric_patient")
    elif age > 70 and level > 2:
        level = max(level - 1, 2)
        flags.append("geriatric_patient")
    return level, flags


def get_recommended_action(level: int) -> str:
    actions = {
        1: "Immediate intervention required. Activate emergency response team.",
        2: "Rapid assessment needed. Assign to physician within 10 minutes.",
        3: "Prompt attention required. Target assessment within 30 minutes.",
        4: "Schedule assessment within 60 minutes. Monitor for changes.",
        5: "Routine care. Assessment within 120 minutes.",
    }
    return actions[level]


def get_vitals_summary(vitals: Vitals) -> dict[str, str]:
    return {
        "heart_rate": f"{vitals.heart_rate} bpm",
        "blood_pressure": f"{vitals.blood_pressure_systolic}/{vitals.blood_pressure_diastolic} mmHg",
        "temperature": f"{vitals.temperature_c}°C",
        "respiratory_rate": f"{vitals.respiratory_rate}/min",
        "oxygen_saturation": f"{vitals.oxygen_saturation}%",
    }


def perform_triage(request: TriageRequest) -> TriageResponse:
    """Run the full triage assessment pipeline."""
    all_flags: list[str] = []

    # Assess each factor
    vitals_level, vitals_flags = assess_vitals(request.vitals)
    all_flags.extend(vitals_flags)

    symptom_level, symptom_flags = assess_symptoms(request.symptoms)
    all_flags.extend(symptom_flags)

    pain_level, pain_flags = assess_pain(request.pain_scale)
    all_flags.extend(pain_flags)

    # Take the most critical level
    level = min(vitals_level, symptom_level, pain_level)

    # Apply age modifier
    level, age_flags = apply_age_modifier(level, request.age)
    all_flags.extend(age_flags)

    # Never go below 1
    level = max(level, 1)

    label, color = PRIORITY_LABELS[level]
    unique_flags = list(dict.fromkeys(all_flags))

    return TriageResponse(
        patient_name=request.patient_name,
        priority_level=level,
        priority_label=label,
        priority_color=color,
        recommended_action=get_recommended_action(level),
        flags=unique_flags,
        vitals_summary=get_vitals_summary(request.vitals),
    )
