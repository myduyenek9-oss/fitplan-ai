from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError, model_validator

from app.core.errors import PlanIntegrityError

MealType = Literal["breakfast", "lunch", "dinner", "snack"]
WorkoutKind = Literal["workout", "rest"]


class MealPlan(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    meal_type: MealType | None = None
    calories: FiniteFloat = Field(gt=0)
    protein_g: FiniteFloat = Field(ge=0)
    carb_g: FiniteFloat = Field(ge=0)
    fat_g: FiniteFloat = Field(ge=0)


class WorkoutPlan(BaseModel):
    kind: WorkoutKind
    title: str = Field(min_length=1, max_length=256)
    instructions: str = Field(min_length=1, max_length=2048)
    duration_minutes: FiniteFloat | None = Field(default=None, gt=0)


class PlanDay(BaseModel):
    date: date
    calorie_target: FiniteFloat = Field(gt=0)
    meals: list[MealPlan] = Field(min_length=1)
    training_instruction: WorkoutPlan


PlanDayCreate = PlanDay


class PlanCreate(BaseModel):
    title: str = Field(default="7-day plan", min_length=1, max_length=256)
    days: list[PlanDay] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_consecutive_days(self) -> "PlanCreate":
        ordered_days = sorted(self.days, key=lambda day: day.date)
        if len({day.date for day in ordered_days}) != 7:
            raise ValueError("plan days must have seven distinct dates")
        expected = ordered_days[0].date
        if any(day.date != expected + timedelta(days=index) for index, day in enumerate(ordered_days)):
            raise ValueError("plan days must be seven consecutive dates")
        if self.days != ordered_days:
            raise ValueError("plan days must be ordered by date")
        return self


class PlanGenerate(BaseModel):
    start_date: date
    title: str = Field(default="7-day plan", min_length=1, max_length=256)


class PlanSummary(BaseModel):
    id: int
    user_id: int
    title: str
    start_date: date
    end_date: date
    is_active: bool
    days: list[PlanDay] = Field(min_length=7, max_length=7)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_plan(cls, plan: Any) -> "PlanSummary":
        try:
            days = [
                PlanDay(
                    date=day.date,
                    calorie_target=day.calorie_target,
                    meals=day.meals,
                    training_instruction=day.training_instruction,
                )
                for day in plan.days
            ]
            validated_plan = PlanCreate(title=plan.title, days=days)
            return cls(
                id=plan.id,
                user_id=plan.user_id,
                title=validated_plan.title,
                start_date=validated_plan.days[0].date,
                end_date=validated_plan.days[-1].date,
                is_active=plan.is_active,
                days=validated_plan.days,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
        except (ValidationError, TypeError, ValueError, AttributeError) as exc:
            raise PlanIntegrityError from exc
