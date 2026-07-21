from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from app.api.time_utils import ensure_timezone_aware
from app.schemas.plan import PlanDayCreate


MAX_FOOD_ITEM_CALORIES = 3000
MAX_FOOD_ITEM_MACROS_G = 500
MAX_FOOD_TOTAL_CALORIES = 6000
MAX_FOOD_TOTAL_MACROS_G = 1000
MAX_EXERCISE_DURATION_MINUTES = 600
MAX_EXERCISE_CALORIES_BURNED = 3000


class ParsedFoodItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=128)
    quantity: str = Field(min_length=1, max_length=64)
    calories: FiniteFloat = Field(ge=0, le=MAX_FOOD_ITEM_CALORIES)
    protein_g: FiniteFloat = Field(ge=0, le=MAX_FOOD_ITEM_MACROS_G)
    carb_g: FiniteFloat = Field(ge=0, le=MAX_FOOD_ITEM_MACROS_G)
    fat_g: FiniteFloat = Field(ge=0, le=MAX_FOOD_ITEM_MACROS_G)


class ParsedFoodResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    meal_type: str | None = Field(default=None, max_length=32)
    logged_at: datetime
    confidence: FiniteFloat = Field(ge=0, le=1)
    items: list[ParsedFoodItem] = Field(min_length=1)
    adjustment_suggestion: str = Field(min_length=1, max_length=1024)

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)

    @model_validator(mode="after")
    def validate_totals_are_reasonable(self) -> "ParsedFoodResult":
        if self.calories > MAX_FOOD_TOTAL_CALORIES:
            raise ValueError("food calories exceed a reasonable single-entry limit")
        if (
            self.protein_g > MAX_FOOD_TOTAL_MACROS_G
            or self.carb_g > MAX_FOOD_TOTAL_MACROS_G
            or self.fat_g > MAX_FOOD_TOTAL_MACROS_G
        ):
            raise ValueError("food macros exceed a reasonable single-entry limit")
        return self

    @property
    def calories(self) -> float:
        return sum(item.calories for item in self.items)

    @property
    def protein_g(self) -> float:
        return sum(item.protein_g for item in self.items)

    @property
    def carb_g(self) -> float:
        return sum(item.carb_g for item in self.items)

    @property
    def fat_g(self) -> float:
        return sum(item.fat_g for item in self.items)


class ParsedExerciseResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    exercise_type: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    duration_minutes: FiniteFloat = Field(gt=0, le=MAX_EXERCISE_DURATION_MINUTES)
    calories_burned: FiniteFloat = Field(gt=0, le=MAX_EXERCISE_CALORIES_BURNED)
    logged_at: datetime
    confidence: FiniteFloat = Field(ge=0, le=1)
    adjustment_suggestion: str = Field(min_length=1, max_length=1024)

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class PlanGenerationResult(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    days: list[PlanDayCreate]
    safety_note: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def validate_day_count(self) -> "PlanGenerationResult":
        if len(self.days) != 7:
            raise ValueError("plan generation must return exactly seven days")
        return self


ConversationRole = Literal["user", "assistant", "system"]


class BoundedContext(BaseModel):
    today: date
    profile: dict | None = None
    current_plan: dict | None = None
    daily_summary: dict | None = None
    recent_messages: list[dict] = Field(default_factory=list, max_length=10)
