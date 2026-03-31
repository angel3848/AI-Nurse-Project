from app.schemas.metrics import BMIRequest, BMIResponse, HealthyWeightRange

BMI_CATEGORIES = [
    (16.0, "severe underweight", "Your BMI indicates severe underweight. Please seek medical advice promptly."),
    (
        17.0,
        "moderate underweight",
        "Your BMI indicates moderate underweight. Consider consulting a healthcare provider.",
    ),
    (
        18.5,
        "underweight",
        "Your BMI indicates underweight. A healthcare provider can help create a healthy weight plan.",
    ),
    (
        25.0,
        "normal",
        "Your BMI is in the healthy range. Maintain your current lifestyle with balanced nutrition and regular activity.",
    ),
    (
        30.0,
        "overweight",
        "Your BMI indicates overweight. Consider consulting a healthcare provider for personalized advice.",
    ),
    (35.0, "obese class I", "Your BMI indicates obesity (class I). Please consult a healthcare provider for guidance."),
    (
        40.0,
        "obese class II",
        "Your BMI indicates obesity (class II). Please seek medical advice for a management plan.",
    ),
    (
        float("inf"),
        "obese class III",
        "Your BMI indicates severe obesity (class III). Please seek medical advice promptly.",
    ),
]


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def get_bmi_category(bmi: float) -> tuple[str, str]:
    for threshold, category, interpretation in BMI_CATEGORIES:
        if bmi < threshold:
            return category, interpretation
    return BMI_CATEGORIES[-1][1], BMI_CATEGORIES[-1][2]


def get_healthy_weight_range(height_cm: float) -> HealthyWeightRange:
    height_m = height_cm / 100
    return HealthyWeightRange(
        min_kg=round(18.5 * height_m**2, 1),
        max_kg=round(24.9 * height_m**2, 1),
    )


LBS_PER_KG = 2.20462
CM_PER_INCH = 2.54


def imperial_to_metric(
    height_ft: float | None, height_in: float | None, weight_lbs: float | None
) -> tuple[float, float]:
    total_inches = (height_ft or 0) * 12 + (height_in or 0)
    height_cm = total_inches * CM_PER_INCH
    weight_kg = (weight_lbs or 0) / LBS_PER_KG
    return height_cm, weight_kg


def assess_bmi(request: BMIRequest) -> BMIResponse:
    if request.unit_system == "imperial":
        height_cm, weight_kg = imperial_to_metric(request.height_ft, request.height_in, request.weight_lbs)
    else:
        height_cm = request.height_cm or 0
        weight_kg = request.weight_kg or 0

    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive values")

    bmi = calculate_bmi(height_cm, weight_kg)
    category, interpretation = get_bmi_category(bmi)
    healthy_range = get_healthy_weight_range(height_cm)

    if request.unit_system == "imperial":
        healthy_range.min_lbs = round(healthy_range.min_kg * LBS_PER_KG, 1)
        healthy_range.max_lbs = round(healthy_range.max_kg * LBS_PER_KG, 1)

    return BMIResponse(
        bmi=bmi,
        category=category,
        healthy_weight_range=healthy_range,
        interpretation=interpretation,
        unit_system=request.unit_system,
    )
