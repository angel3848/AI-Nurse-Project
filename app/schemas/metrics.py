from pydantic import BaseModel, Field


class BMIRequest(BaseModel):
    height_cm: float = Field(..., gt=0, le=300, description="Height in centimeters")
    weight_kg: float = Field(..., gt=0, le=700, description="Weight in kilograms")


class HealthyWeightRange(BaseModel):
    min_kg: float
    max_kg: float


class BMIResponse(BaseModel):
    bmi: float
    category: str
    healthy_weight_range: HealthyWeightRange
    interpretation: str
