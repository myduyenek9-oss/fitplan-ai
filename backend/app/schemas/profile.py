from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.time_utils import ensure_timezone_aware, validate_timezone_name

Sex = Literal["male", "female", "other", "unspecified"]
GoalType = Literal["fat_loss", "maintenance", "muscle_gain"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]


class ProfileUpsert(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    sex: Sex | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, ge=100, le=230)

    @field_validator("birth_date")
    @classmethod
    def validate_adult_age(cls, value: date | None) -> date | None:
        if value is None:
            return None
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18 or age > 100:
            raise ValueError("age must be between 18 and 100")
        return value
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_timezone_name(value)


class ProfileResponse(ProfileUpsert):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalUpsert(BaseModel):
    goal_type: GoalType
    daily_calories: float = Field(ge=1000, le=6000)
    protein_g: float = Field(gt=0)
    carb_g: float = Field(gt=0)
    fat_g: float = Field(gt=0)
    activity_level: ActivityLevel
    target_weight_kg: float | None = Field(default=None, ge=30, le=250)
    target_date: date | None = None


class GoalResponse(GoalUpsert):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BodyMetricCreate(BaseModel):
    weight_kg: float | None = Field(default=None, ge=30, le=250)
    body_fat_percent: float | None = Field(default=None, ge=0, le=100)
    waist_cm: float | None = Field(default=None, gt=0)
    chest_cm: float | None = Field(default=None, gt=0)
    hip_cm: float | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=1024)
    logged_at: datetime

    @field_validator("logged_at")
    @classmethod
    def validate_logged_at(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class BodyMetricResponse(BodyMetricCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
