from app.schemas.metrics import BMIRequest, BMIResponse, HealthyWeightRange

BMI_CATEGORIES = [
    (16.0, "severe underweight", "Your BMI indicates severe underweight. Please seek medical advice promptly."),
    (17.0, "moderate underweight", "Your BMI indicates moderate underweight. Consider consulting a healthcare provider."),
    (18.5, "underweight", "Your BMI indicates underweight. A healthcare provider can help create a healthy weight plan."),
    (25.0, "normal", "Your BMI is in the healthy range. Maintain your current lifestyle with balanced nutrition and regular activity."),
    (30.0, "overweight", "Your BMI indicates overweight. Consider consulting a healthcare provider for personalized advice."),
    (35.0, "obese class I", "Your BMI indicates obesity (class I). Please consult a healthcare provider for guidance."),
    (40.0, "obese class II", "Your BMI indicates obesity (class II). Please seek medical advice for a management plan."),
    (float("inf"), "obese class III", "Your BMI indicates severe obesity (class III). Please seek medical advice promptly."),
]


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def get_bmi_category(bmi: float) -> tuple[str, str]:
    for threshold, category, interpretation in BMI_CATEGORIES:
        if bmi < threshold:
            return category, interpretation
    return BMI_CATEGORIES[-1][1], BMI_CATEGORIES[-1][2]


def get_healthy_weight_range(height_cm: float) -> HealthyWeightRange:
    height_m = height_cm / 100
    return HealthyWeightRange(
        min_kg=round(18.5 * height_m ** 2, 1),
        max_kg=round(24.9 * height_m ** 2, 1),
    )


def assess_bmi(request: BMIRequest) -> BMIResponse:
    bmi = calculate_bmi(request.height_cm, request.weight_kg)
    category, interpretation = get_bmi_category(bmi)
    healthy_range = get_healthy_weight_range(request.height_cm)

    return BMIResponse(
        bmi=bmi,
        category=category,
        healthy_weight_range=healthy_range,
        interpretation=interpretation,
    )
