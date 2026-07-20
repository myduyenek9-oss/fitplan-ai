from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.time_utils import (
    get_user_timezone,
    local_date_to_utc_naive_bounds,
    to_utc_naive,
    utc_naive_to_timezone,
)
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


def _food_log_response(record: FoodLog, user_timezone) -> FoodLogResponse:
    return FoodLogResponse(
        id=record.id,
        user_id=record.user_id,
        original_text=record.original_text,
        parsed_content=record.parsed_content,
        meal_type=record.meal_type,
        calories=record.calories,
        protein_g=record.protein_g,
        carb_g=record.carb_g,
        fat_g=record.fat_g,
        status=record.status,
        logged_at=utc_naive_to_timezone(record.logged_at, user_timezone),
        created_at=utc_naive_to_timezone(record.created_at, user_timezone),
        updated_at=utc_naive_to_timezone(record.updated_at, user_timezone),
    )


def _exercise_log_response(record: ExerciseLog, user_timezone) -> ExerciseLogResponse:
    return ExerciseLogResponse(
        id=record.id,
        user_id=record.user_id,
        exercise_type=record.exercise_type,
        description=record.description,
        duration_minutes=record.duration_minutes,
        calories_burned=record.calories_burned,
        logged_at=utc_naive_to_timezone(record.logged_at, user_timezone),
        created_at=utc_naive_to_timezone(record.created_at, user_timezone),
        updated_at=utc_naive_to_timezone(record.updated_at, user_timezone),
    )



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
) -> FoodLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    values = payload.model_dump()
    values["logged_at"] = to_utc_naive(payload.logged_at)
    record = FoodLog(user_id=current_user.id, status="active", **values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _food_log_response(record, user_timezone)


@router.post("/exercise", response_model=ExerciseLogResponse, status_code=status.HTTP_201_CREATED)
def create_exercise_log(
    payload: ExerciseLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    values = payload.model_dump()
    values["logged_at"] = to_utc_naive(payload.logged_at)
    record = ExerciseLog(user_id=current_user.id, **values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _exercise_log_response(record, user_timezone)


@router.get("/daily", response_model=DailySummaryResponse)
def get_daily_summary(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailySummaryResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    start, end = local_date_to_utc_naive_bounds(date_, user_timezone)
    food_logs = list(
        db.scalars(
            select(FoodLog).where(
                FoodLog.user_id == current_user.id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at < end,
            )
        )
    )
    exercise_logs = list(
        db.scalars(
            select(ExerciseLog).where(
                ExerciseLog.user_id == current_user.id,
                ExerciseLog.logged_at >= start,
                ExerciseLog.logged_at < end,
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
        select(Goal)
        .where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
        .order_by(Goal.updated_at.desc(), Goal.id.desc())
        .limit(1)
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
) -> FoodLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    record = _get_user_food_log(db, current_user, record_id)
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    non_nullable_fields = {
        "original_text",
        "parsed_content",
        "calories",
        "protein_g",
        "carb_g",
        "fat_g",
        "logged_at",
    }
    null_fields = [field for field in non_nullable_fields if values.get(field) is None and field in values]
    if null_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Fields cannot be null: {', '.join(sorted(null_fields))}",
        )
    if "logged_at" in values:
        values["logged_at"] = to_utc_naive(values["logged_at"])
    for field, value in values.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return _food_log_response(record, user_timezone)


@router.delete("/food/{record_id}", response_model=FoodLogResponse)
def delete_food_log(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    record = _get_user_food_log(db, current_user, record_id)
    record.status = "deleted"
    db.commit()
    db.refresh(record)
    return _food_log_response(record, user_timezone)


@router.post("/food/{record_id}/undo", response_model=FoodLogResponse)
def undo_food_log(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    record = _get_user_food_log(db, current_user, record_id)
    record.status = "undone"
    db.commit()
    db.refresh(record)
    return _food_log_response(record, user_timezone)
