from datetime import UTC, date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.goal import Goal
from app.models.record import ExerciseLog, FoodLog
from app.models.user import User
from app.schemas.record import (
    DailyGoalSnapshot,
    DailySummaryResponse,
    ExerciseLogCreate,
    ExerciseLogResponse,
    ExerciseTotals,
    FoodLogCreate,
    FoodLogResponse,
    FoodLogUpdate,
    FoodTotals,
    MacroCompletionPercentages,
)

router = APIRouter(prefix="/api/records", tags=["records"])


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _utc_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)
    return start, end


def _get_user_food_log(db: Session, current_user: User, record_id: int) -> FoodLog:
    record = db.get(FoodLog, record_id)
    if record is None or record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food record not found")
    return record


def _round_percent(value: float, target: float) -> float | None:
    if target <= 0:
        return None
    return round((value / target) * 100, 2)


@router.post("/food", response_model=FoodLogResponse, status_code=status.HTTP_201_CREATED)
def create_food_log(
    payload: FoodLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLog:
    values = payload.model_dump()
    values["logged_at"] = to_utc_naive(payload.logged_at)
    record = FoodLog(user_id=current_user.id, status="active", **values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/exercise", response_model=ExerciseLogResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_log(
    payload: ExerciseLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseLog:
    values = payload.model_dump()
    values["logged_at"] = to_utc_naive(payload.logged_at)
    record = ExerciseLog(user_id=current_user.id, **values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/daily", response_model=DailySummaryResponse)
def get_daily_summary(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailySummaryResponse:
    start, end = _utc_day_bounds(date_)
    food_logs = list(
        db.scalars(
            select(FoodLog).where(
                FoodLog.user_id == current_user.id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at <= end,
            )
        )
    )
    exercise_logs = list(
        db.scalars(
            select(ExerciseLog).where(
                ExerciseLog.user_id == current_user.id,
                ExerciseLog.logged_at >= start,
                ExerciseLog.logged_at <= end,
            )
        )
    )
    active_food_logs = [record for record in food_logs if record.status == "active"]

    food_totals = FoodTotals(
        calories=sum(record.calories for record in active_food_logs),
        protein_g=sum(record.protein_g for record in active_food_logs),
        carb_g=sum(record.carb_g for record in active_food_logs),
        fat_g=sum(record.fat_g for record in active_food_logs),
    )
    exercise_totals = ExerciseTotals(
        calories_burned=sum(record.calories_burned for record in exercise_logs),
        duration_minutes=sum(record.duration_minutes for record in exercise_logs),
    )
    active_goal = db.scalar(
        select(Goal).where(Goal.user_id == current_user.id, Goal.is_active.is_(True)).limit(1)
    )

    goal_snapshot: DailyGoalSnapshot | None = None
    remaining_calories: float | None = None
    macro_percentages = MacroCompletionPercentages(protein_g=None, carb_g=None, fat_g=None)
    if active_goal is not None:
        goal_snapshot = DailyGoalSnapshot(
            daily_calories=active_goal.daily_calories,
            protein_g=active_goal.protein_g,
            carb_g=active_goal.carb_g,
            fat_g=active_goal.fat_g,
        )
        remaining_calories = (
            active_goal.daily_calories - food_totals.calories + exercise_totals.calories_burned
        )
        macro_percentages = MacroCompletionPercentages(
            protein_g=_round_percent(food_totals.protein_g, active_goal.protein_g),
            carb_g=_round_percent(food_totals.carb_g, active_goal.carb_g),
            fat_g=_round_percent(food_totals.fat_g, active_goal.fat_g),
        )

    status_counts: dict[str, int] = {"active": 0, "deleted": 0, "undone": 0}
    for record in food_logs:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1

    return DailySummaryResponse(
        date=date_,
        goal=goal_snapshot,
        food_totals=food_totals,
        exercise_totals=exercise_totals,
        remaining_calories=remaining_calories,
        macro_completion_percentages=macro_percentages,
        food_status_counts=status_counts,
    )


@router.patch("/food/{record_id}", response_model=FoodLogResponse)
def update_food_log(
    record_id: int,
    payload: FoodLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLog:
    record = _get_user_food_log(db, current_user, record_id)
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if "logged_at" in values and values["logged_at"] is not None:
        values["logged_at"] = to_utc_naive(values["logged_at"])
    for field, value in values.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/food/{record_id}", response_model=FoodLogResponse)
def delete_food_log(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLog:
    record = _get_user_food_log(db, current_user, record_id)
    record.status = "deleted"
    db.commit()
    db.refresh(record)
    return record


@router.post("/food/{record_id}/undo", response_model=FoodLogResponse)
def undo_food_log(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLog:
    record = _get_user_food_log(db, current_user, record_id)
    record.status = "undone"
    db.commit()
    db.refresh(record)
    return record
