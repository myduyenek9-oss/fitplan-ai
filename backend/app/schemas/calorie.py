"""Calorie and macronutrient target schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["fat_loss", "maintenance", "muscle_gain"]
Sex = Literal["male", "female"]


class CaloriePreviewRequest(BaseModel):
    age: int = Field(ge=13, le=100)
    sex: Sex
    weight_kg: float = Field(ge=30, le=250)
    height_cm: float = Field(ge=100, le=230)
    activity_level: ActivityLevel
    goal: Goal

    @field_validator("sex", "activity_level", "goal", mode="before")
    @classmethod
    def normalize_choice(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class CalorieTargets(BaseModel):
    bmr: int
    tdee: int
    daily_calories: int
    protein_g: int
    carb_g: int
    fat_g: int
