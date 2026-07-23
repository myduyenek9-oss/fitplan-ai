from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.ai import get_ai_client
from app.api.deps import get_current_user, get_db
from app.api.time_utils import (
    get_user_timezone,
    local_date_to_utc_storage_bounds,
    to_utc_storage,
    utc_storage_to_timezone,
)
from app.models.goal import Goal
from app.models.record import ExerciseLog, FoodLog
from app.models.user import User
from app.schemas.chat import (
    NaturalLanguageExerciseRecordResponse,
    NaturalLanguageFoodRecordResponse,
    NaturalLanguageRecordRequest,
)
from app.schemas.record import (
    CalorieCalculation,
    DailyGoalSnapshot,
    DailySummaryResponse,
    ExerciseLogCreate,
    ExerciseLogResponse,
    ExerciseLogUpdate,
    ExerciseTotals,
    FoodLogCreate,
    FoodLogResponse,
    FoodLogUpdate,
    FoodTotals,
    MacroCompletionPercentages,
)
from app.services.ai_client import AiClient
from app.services.ai_record_service import AiRecordError, AiRecordService
from app.services.record_detection import looks_like_completed_exercise, looks_like_mixed_completed_records

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
        calories_min=(record.parsed_content.get("estimate_range", {}) or {}).get("calories_min"),
        calories_max=(record.parsed_content.get("estimate_range", {}) or {}).get("calories_max"),
        status=record.status,
        logged_at=utc_storage_to_timezone(record.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(record.created_at, user_timezone),
        updated_at=utc_storage_to_timezone(record.updated_at, user_timezone),
    )


def _exercise_log_response(record: ExerciseLog, user_timezone) -> ExerciseLogResponse:
    return ExerciseLogResponse(
        id=record.id,
        user_id=record.user_id,
        original_text=record.original_text,
        exercise_type=record.exercise_type,
        description=record.description,
        duration_minutes=record.duration_minutes,
        calories_burned=record.calories_burned,
        calories_burned_min=round(record.calories_burned * 0.8, 2),
        calories_burned_max=round(record.calories_burned * 1.2, 2),
        logged_at=utc_storage_to_timezone(record.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(record.created_at, user_timezone),
        updated_at=utc_storage_to_timezone(record.updated_at, user_timezone),
    )



def _get_user_food_log(db: Session, current_user: User, record_id: int) -> FoodLog:
    record = db.get(FoodLog, record_id)
    if record is None or record.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food record not found")
    return record


def _get_user_exercise_log(
    db: Session, current_user: User, record_id: int
) -> ExerciseLog:
    record = db.get(ExerciseLog, record_id)
    if record is None or record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise record not found",
        )
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
    values["logged_at"] = to_utc_storage(payload.logged_at)
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
    values["logged_at"] = to_utc_storage(payload.logged_at)
    record = ExerciseLog(user_id=current_user.id, **values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _exercise_log_response(record, user_timezone)




@router.post("/exercise/{record_id}/undo", status_code=status.HTTP_204_NO_CONTENT)
def undo_exercise_log(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    record = _get_user_exercise_log(db, current_user, record_id)
    db.delete(record)
    db.commit()


@router.post(
    "/food/natural-language",
    response_model=NaturalLanguageFoodRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_food_log_from_natural_language(
    payload: NaturalLanguageRecordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AiClient = Depends(get_ai_client),
) -> NaturalLanguageFoodRecordResponse:
    target_day = payload.today or date.today()
    is_mixed_record = looks_like_mixed_completed_records(payload.text)
    is_pure_exercise = looks_like_completed_exercise(payload.text) and not is_mixed_record
    try:
        if is_pure_exercise:
            exercise_result = await AiRecordService(ai_client=ai_client).create_exercise_from_text(
                db,
                user_id=current_user.id,
                text=payload.text,
                today=target_day,
            )
            return NaturalLanguageFoodRecordResponse(
                record=exercise_result.record,
                recorded_food=None,
                recorded_exercise=exercise_result.record,
                daily_summary=exercise_result.daily_summary,
                adjustment_suggestion=exercise_result.adjustment_suggestion,
                conversation_id=exercise_result.conversation_id,
            )

        result = await AiRecordService(ai_client=ai_client).create_food_from_text(
            db,
            user_id=current_user.id,
            text=payload.text,
            today=target_day,
        )
    except AiRecordError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return NaturalLanguageFoodRecordResponse(
        record=result.record,
        recorded_food=result.record,
        recorded_exercise=result.recorded_exercise,
        daily_summary=result.daily_summary,
        adjustment_suggestion=result.adjustment_suggestion,
        conversation_id=result.conversation_id,
    )


@router.post(
    "/exercise/natural-language",
    response_model=NaturalLanguageExerciseRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_log_from_natural_language(
    payload: NaturalLanguageRecordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AiClient = Depends(get_ai_client),
) -> NaturalLanguageExerciseRecordResponse:
    try:
        result = await AiRecordService(ai_client=ai_client).create_exercise_from_text(
            db,
            user_id=current_user.id,
            text=payload.text,
            today=payload.today or date.today(),
        )
    except AiRecordError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return NaturalLanguageExerciseRecordResponse(
        record=result.record,
        daily_summary=result.daily_summary,
        adjustment_suggestion=result.adjustment_suggestion,
        conversation_id=result.conversation_id,
    )


@router.get("/daily", response_model=DailySummaryResponse)
def get_daily_summary(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailySummaryResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    start, end = local_date_to_utc_storage_bounds(date_, user_timezone)
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
        calorie_calculation=CalorieCalculation(
            formula="\u76ee\u6807\u70ed\u91cf - \u5df2\u6444\u5165\u98df\u7269\u70ed\u91cf + \u8fd0\u52a8\u6d88\u8017",
            exercise_included_fully=True,
            explanation="\u8fd0\u52a8\u6d88\u8017\u4f1a\u5168\u90e8\u8ba1\u5165\u53ef\u6444\u5165\u989d\u5ea6\uff0c\u4f46\u4f30\u7b97\u6709\u8bef\u5dee\uff0c\u8bf7\u4ec5\u4f5c\u53c2\u8003\u3002",
        ),
        macro_completion_percentages=macro_percentages,
        food_status_counts=status_counts,
        food_records=[
            _food_log_response(record, user_timezone)
            for record in sorted(active_food_logs, key=lambda item: (item.logged_at, item.id), reverse=True)
        ],
        exercise_records=[
            _exercise_log_response(record, user_timezone)
            for record in sorted(exercise_logs, key=lambda item: (item.logged_at, item.id), reverse=True)
        ],
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
        values["logged_at"] = to_utc_storage(values["logged_at"])
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


@router.patch("/exercise/{record_id}", response_model=ExerciseLogResponse)
def update_exercise_log(
    record_id: int,
    payload: ExerciseLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseLogResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    record = _get_user_exercise_log(db, current_user, record_id)
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if "logged_at" in values:
        if values["logged_at"] is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="logged_at cannot be null")
        values["logged_at"] = to_utc_storage(values["logged_at"])
    for field, value in values.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return _exercise_log_response(record, user_timezone)
