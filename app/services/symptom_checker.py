from app.schemas.symptom import (
    PossibleCondition,
    SymptomCheckRequest,
    SymptomCheckResponse,
)

# Condition database: maps symptom combinations to possible conditions.
# Each entry: (required_symptoms, condition_name, description, category)
CONDITION_DATABASE: list[tuple[set[str], str, str, str]] = [
    # Respiratory
    (
        {"fever", "cough", "fatigue", "body_aches"},
        "Influenza",
        "Viral infection with fever, cough, and body aches lasting 1-2 weeks",
        "respiratory",
    ),
    (
        {"fever", "cough", "shortness_of_breath"},
        "Pneumonia",
        "Lung infection causing cough, fever, and breathing difficulty",
        "respiratory",
    ),
    (
        {"cough", "runny_nose", "sore_throat"},
        "Common Cold",
        "Upper respiratory viral infection with mild symptoms",
        "respiratory",
    ),
    (
        {"shortness_of_breath", "wheezing", "cough"},
        "Asthma Exacerbation",
        "Airway narrowing causing wheezing and breathing difficulty",
        "respiratory",
    ),
    (
        {"sore_throat", "fever", "swollen_glands"},
        "Strep Throat",
        "Bacterial throat infection requiring antibiotic treatment",
        "respiratory",
    ),
    # Cardiac
    (
        {"chest_pain", "shortness_of_breath", "sweating"},
        "Possible Cardiac Event",
        "Chest pain with sweating and shortness of breath requires immediate evaluation",
        "cardiac",
    ),
    (
        {"chest_pain", "shortness_of_breath"},
        "Angina",
        "Chest pain due to reduced blood flow to the heart",
        "cardiac",
    ),
    # Gastrointestinal
    (
        {"nausea", "vomiting", "diarrhea"},
        "Gastroenteritis",
        "Stomach and intestinal inflammation, often viral",
        "gastrointestinal",
    ),
    (
        {"abdominal_pain", "nausea", "fever"},
        "Appendicitis",
        "Inflammation of the appendix requiring medical evaluation",
        "gastrointestinal",
    ),
    (
        {"abdominal_pain", "bloating", "nausea"},
        "Gastritis",
        "Stomach lining inflammation causing pain and nausea",
        "gastrointestinal",
    ),
    # Neurological
    (
        {"headache", "nausea", "light_sensitivity"},
        "Migraine",
        "Severe headache often with nausea and sensitivity to light",
        "neurological",
    ),
    (
        {"headache", "fever", "stiff_neck"},
        "Meningitis",
        "Serious infection of brain membranes requiring emergency care",
        "neurological",
    ),
    (
        {"dizziness", "nausea", "balance_problems"},
        "Vertigo",
        "Inner ear or neurological condition causing spinning sensation",
        "neurological",
    ),
    # Musculoskeletal
    (
        {"joint_pain", "swelling", "stiffness"},
        "Arthritis Flare",
        "Joint inflammation causing pain, swelling, and reduced mobility",
        "musculoskeletal",
    ),
    (
        {"back_pain", "numbness", "weakness"},
        "Sciatica",
        "Nerve compression causing back pain radiating to legs",
        "musculoskeletal",
    ),
    # Infectious
    (
        {"fever", "rash", "fatigue"},
        "Viral Infection",
        "General viral illness with systemic symptoms",
        "infectious",
    ),
    (
        {"fever", "chills", "body_aches", "fatigue"},
        "Systemic Infection",
        "Body-wide infection requiring medical evaluation",
        "infectious",
    ),
    # Dermatological
    (
        {"rash", "itching", "swelling"},
        "Allergic Reaction",
        "Immune response to allergen causing skin symptoms",
        "dermatological",
    ),
    # Urological
    (
        {"painful_urination", "frequent_urination", "fever"},
        "Urinary Tract Infection",
        "Bacterial infection of the urinary system",
        "urological",
    ),
]

URGENCY_MAP = {
    "cardiac": "high",
    "neurological": "moderate",
    "respiratory": "moderate",
    "gastrointestinal": "moderate",
    "infectious": "moderate",
    "musculoskeletal": "low",
    "dermatological": "low",
    "urological": "moderate",
}

EMERGENCY_CONDITIONS = {"Possible Cardiac Event", "Meningitis", "Appendicitis"}


def match_conditions(
    symptoms: list[str],
) -> list[tuple[str, float, str, str]]:
    """Match symptoms against condition database, returning scored results."""
    symptom_set = {s.lower() for s in symptoms}
    matches: list[tuple[str, float, str, str]] = []

    for required, name, description, category in CONDITION_DATABASE:
        overlap = symptom_set & required
        if len(overlap) >= 2 or (len(required) <= 2 and overlap == required):
            score = len(overlap) / len(required)
            matches.append((name, score, description, category))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def score_to_probability(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "moderate"
    return "low"


def determine_urgency(
    conditions: list[tuple[str, float, str, str]],
    severity: str,
    duration_days: int,
    age: int,
) -> str:
    """Determine overall urgency based on conditions and context."""
    if not conditions:
        if severity == "severe":
            return "moderate"
        return "low"

    # Check for emergency conditions
    for name, _, _, _ in conditions:
        if name in EMERGENCY_CONDITIONS:
            return "emergency"

    # Get highest urgency from matched categories
    category_urgencies = {"high": 3, "moderate": 2, "low": 1, "emergency": 4}
    max_urgency = "low"
    for _, _, _, category in conditions:
        cat_urgency = URGENCY_MAP.get(category, "low")
        if category_urgencies.get(cat_urgency, 0) > category_urgencies.get(max_urgency, 0):
            max_urgency = cat_urgency

    # Severity modifier
    if severity == "severe" and max_urgency == "low":
        max_urgency = "moderate"

    # Duration modifier — acute onset is more concerning
    if duration_days <= 1 and max_urgency in ("low", "moderate"):
        urgency_levels = ["low", "moderate", "high"]
        idx = urgency_levels.index(max_urgency)
        max_urgency = urgency_levels[min(idx + 1, 2)]

    # Age modifier
    if (age < 5 or age > 70) and max_urgency == "low":
        max_urgency = "moderate"

    return max_urgency


def get_recommended_action(urgency: str) -> str:
    actions = {
        "emergency": "Seek emergency medical care immediately. Call emergency services or go to the nearest emergency room.",
        "high": "See a doctor as soon as possible, ideally within 24 hours.",
        "moderate": "Schedule a doctor's appointment within a few days. Monitor symptoms and seek immediate care if they worsen.",
        "low": "Monitor symptoms at home. Practice self-care and see a doctor if symptoms persist beyond a week or worsen.",
    }
    return actions[urgency]


def check_symptoms(request: SymptomCheckRequest) -> SymptomCheckResponse:
    """Analyze symptoms and return possible conditions with recommendations."""
    matches = match_conditions(request.symptoms)

    possible_conditions = [
        PossibleCondition(
            condition=name,
            probability=score_to_probability(score),
            description=description,
            category=category,
        )
        for name, score, description, category in matches[:5]
    ]

    urgency = determine_urgency(matches, request.severity, request.duration_days, request.age)
    recommended_action = get_recommended_action(urgency)

    return SymptomCheckResponse(
        possible_conditions=possible_conditions,
        recommended_action=recommended_action,
        urgency=urgency,
    )
