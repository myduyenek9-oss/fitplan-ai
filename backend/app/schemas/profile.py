from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Sex = Literal["male", "female", "other", "unspecified"]
GoalType = Literal["fat_loss", "maintenance", "muscle_gain"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]


class ProfileUpsert(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    sex: Sex | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, ge=0, le=300)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ProfileResponse(ProfileUpsert):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalUpsert(BaseModel):
    goal_type: GoalType
    daily_calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carb_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    activity_level: ActivityLevel
    target_weight_kg: float | None = Field(default=None, ge=0)
    target_date: date | None = None


class GoalResponse(GoalUpsert):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BodyMetricCreate(BaseModel):
    weight_kg: float | None = Field(default=None, ge=0)
    body_fat_percent: float | None = Field(default=None, ge=0, le=100)
    waist_cm: float | None = Field(default=None, ge=0)
    chest_cm: float | None = Field(default=None, ge=0)
    hip_cm: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1024)
    logged_at: datetime


class BodyMetricResponse(BodyMetricCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
