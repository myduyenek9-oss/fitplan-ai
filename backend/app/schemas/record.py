from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.time_utils import ensure_timezone_aware

FoodStatus = Literal["active", "deleted", "undone"]


class FoodLogCreate(BaseModel):
    original_text: str = Field(min_length=1, max_length=2048)
    parsed_content: dict[str, Any] = Field(default_factory=dict)
    meal_type: str | None = Field(default=None, max_length=32)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carb_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    logged_at: datetime

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class FoodLogUpdate(BaseModel):
    original_text: str | None = Field(default=None, min_length=1, max_length=2048)
    parsed_content: dict[str, Any] | None = None
    meal_type: str | None = Field(default=None, max_length=32)
    calories: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carb_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    logged_at: datetime | None = None

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_timezone_aware(value)


class FoodLogResponse(BaseModel):
    id: int
    user_id: int
    original_text: str
    parsed_content: dict[str, Any]
    meal_type: str | None
    calories: float
    protein_g: float
    carb_g: float
    fat_g: float
    calories_min: float | None = None
    calories_max: float | None = None
    status: FoodStatus
    logged_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExerciseLogCreate(BaseModel):
    original_text: str | None = Field(default=None, max_length=2048)
    exercise_type: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    duration_minutes: float = Field(gt=0)
    calories_burned: float = Field(gt=0)
    logged_at: datetime

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class ExerciseLogUpdate(BaseModel):
    original_text: str | None = Field(default=None, max_length=2048)
    exercise_type: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    duration_minutes: float | None = Field(default=None, gt=0)
    calories_burned: float | None = Field(default=None, gt=0)
    logged_at: datetime | None = None

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value) if value is not None else None


class ExerciseLogResponse(ExerciseLogCreate):
    id: int
    calories_burned_min: float | None = None
    calories_burned_max: float | None = None
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FoodTotals(BaseModel):
    calories: float
    protein_g: float
    carb_g: float
    fat_g: float


class ExerciseTotals(BaseModel):
    calories_burned: float
    duration_minutes: float


class CalorieCalculation(BaseModel):
    formula: str
    exercise_included_fully: bool
    explanation: str


class MacroCompletionPercentages(BaseModel):
    protein_g: float | None
    carb_g: float | None
    fat_g: float | None


class DailyGoalSnapshot(BaseModel):
    daily_calories: float
    protein_g: float
    carb_g: float
    fat_g: float


class DailySummaryResponse(BaseModel):
    date: date
    goal: DailyGoalSnapshot | None
    food_totals: FoodTotals
    exercise_totals: ExerciseTotals
    remaining_calories: float | None
    calorie_calculation: CalorieCalculation
    macro_completion_percentages: MacroCompletionPercentages
    food_status_counts: dict[FoodStatus, int]
    food_records: list[FoodLogResponse] = Field(default_factory=list)
    exercise_records: list[ExerciseLogResponse] = Field(default_factory=list)
