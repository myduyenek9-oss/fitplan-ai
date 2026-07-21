from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.time_utils import (
    get_user_timezone,
    local_date_to_utc_storage_bounds,
    to_utc_storage,
)
from app.models.conversation import ConversationMessage
from app.models.goal import Goal
from app.models.record import ExerciseLog, FoodLog
from app.schemas.record import (
    DailyGoalSnapshot,
    DailySummaryResponse,
    ExerciseLogResponse,
    ExerciseTotals,
    FoodLogResponse,
    FoodTotals,
    MacroCompletionPercentages,
)
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_prompts import EXERCISE_PARSE_SYSTEM_PROMPT, FOOD_PARSE_SYSTEM_PROMPT
from app.services.ai_schemas import ParsedExerciseResult, ParsedFoodResult


class AiRecordError(RuntimeError):
    """Raised when a natural-language record cannot be safely created."""


@dataclass(frozen=True)
class FoodNaturalLanguageResult:
    record: FoodLogResponse
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int


@dataclass(frozen=True)
class ExerciseNaturalLanguageResult:
    record: ExerciseLogResponse
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int


class AiRecordService:
    def __init__(self, *, ai_client: AiClient) -> None:
        self.ai_client = ai_client

    async def create_food_from_text(
        self,
        db: Session,
        *,
        user_id: int,
        text: str,
        today: date,
    ) -> FoodNaturalLanguageResult:
        user_message = self._store_user_message(
            db,
            user_id=user_id,
            text=text,
            source="food_natural_language",
        )
        try:
            raw_result = await self.ai_client.chat_json(
                system=FOOD_PARSE_SYSTEM_PROMPT,
                user=self._record_user_prompt(text=text, today=today),
            )
            parsed = ParsedFoodResult.model_validate(raw_result)
        except AiProviderError as exc:
            self._mark_failed(db, user_message, reason=str(exc))
            raise AiRecordError(str(exc)) from exc
        except (ValidationError, TypeError, ValueError) as exc:
            self._mark_failed(db, user_message, reason="AI returned invalid food data")
            raise AiRecordError("AI returned invalid food data") from exc

        user_timezone = get_user_timezone(db, user_id)
        record = FoodLog(
            user_id=user_id,
            original_text=text,
            parsed_content={
                **parsed.model_dump(mode="json"),
                "estimated": True,
                "source": "ai",
            },
            meal_type=parsed.meal_type,
            calories=round(parsed.calories, 2),
            protein_g=round(parsed.protein_g, 2),
            carb_g=round(parsed.carb_g, 2),
            fat_g=round(parsed.fat_g, 2),
            status="active",
            logged_at=to_utc_storage(parsed.logged_at),
        )
        db.add(record)
        db.flush()
        assistant_message = ConversationMessage(
            user_id=user_id,
            role="assistant",
            content=parsed.adjustment_suggestion,
            source="food_natural_language",
            metadata_json={"status": "success", "record_id": record.id, "record_type": "food"},
        )
        user_message.metadata_json = {"status": "success", "record_id": record.id, "record_type": "food"}
        db.add(assistant_message)
        db.commit()
        db.refresh(record)
        db.refresh(assistant_message)
        return FoodNaturalLanguageResult(
            record=_food_response(record, user_timezone),
            daily_summary=build_daily_summary(db, user_id=user_id, day=today),
            adjustment_suggestion=parsed.adjustment_suggestion,
            conversation_id=assistant_message.id,
        )

    async def create_exercise_from_text(
        self,
        db: Session,
        *,
        user_id: int,
        text: str,
        today: date,
    ) -> ExerciseNaturalLanguageResult:
        user_message = self._store_user_message(
            db,
            user_id=user_id,
            text=text,
            source="exercise_natural_language",
        )
        try:
            raw_result = await self.ai_client.chat_json(
                system=EXERCISE_PARSE_SYSTEM_PROMPT,
                user=self._record_user_prompt(text=text, today=today),
            )
            parsed = ParsedExerciseResult.model_validate(raw_result)
        except AiProviderError as exc:
            self._mark_failed(db, user_message, reason=str(exc))
            raise AiRecordError(str(exc)) from exc
        except (ValidationError, TypeError, ValueError) as exc:
            self._mark_failed(db, user_message, reason="AI returned invalid exercise data")
            raise AiRecordError("AI returned invalid exercise data") from exc

        user_timezone = get_user_timezone(db, user_id)
        record = ExerciseLog(
            user_id=user_id,
            exercise_type=parsed.exercise_type,
            description=parsed.description,
            duration_minutes=round(parsed.duration_minutes, 2),
            calories_burned=round(parsed.calories_burned, 2),
            logged_at=to_utc_storage(parsed.logged_at),
        )
        db.add(record)
        db.flush()
        assistant_message = ConversationMessage(
            user_id=user_id,
            role="assistant",
            content=parsed.adjustment_suggestion,
            source="exercise_natural_language",
            metadata_json={"status": "success", "record_id": record.id, "record_type": "exercise"},
        )
        user_message.metadata_json = {
            "status": "success",
            "record_id": record.id,
            "record_type": "exercise",
        }
        db.add(assistant_message)
        db.commit()
        db.refresh(record)
        db.refresh(assistant_message)
        return ExerciseNaturalLanguageResult(
            record=_exercise_response(record, user_timezone),
            daily_summary=build_daily_summary(db, user_id=user_id, day=today),
            adjustment_suggestion=parsed.adjustment_suggestion,
            conversation_id=assistant_message.id,
        )

    @staticmethod
    def _record_user_prompt(*, text: str, today: date) -> str:
        return json.dumps(
            {
                "source_text": text,
                "today": today.isoformat(),
                "instructions": "Parse the record and estimate nutrition or exercise values. Return JSON only.",
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _store_user_message(
        db: Session,
        *,
        user_id: int,
        text: str,
        source: str,
    ) -> ConversationMessage:
        message = ConversationMessage(
            user_id=user_id,
            role="user",
            content=text,
            source=source,
            metadata_json={"status": "pending"},
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def _mark_failed(db: Session, message: ConversationMessage, *, reason: str) -> None:
        message.metadata_json = {"status": "failed", "reason": reason}
        db.commit()


def build_daily_summary(db: Session, *, user_id: int, day: date) -> DailySummaryResponse:
    user_timezone = get_user_timezone(db, user_id)
    start, end = local_date_to_utc_storage_bounds(day, user_timezone)
    food_logs = list(
        db.scalars(
            select(FoodLog).where(
                FoodLog.user_id == user_id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at < end,
            )
        )
    )
    exercise_logs = list(
        db.scalars(
            select(ExerciseLog).where(
                ExerciseLog.user_id == user_id,
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
        .where(Goal.user_id == user_id, Goal.is_active.is_(True))
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
        date=day,
        goal=goal_snapshot,
        food_totals=food_totals,
        exercise_totals=exercise_totals,
        remaining_calories=remaining_calories,
        macro_completion_percentages=macro_percentages,
        food_status_counts=status_counts,
    )


def _round_percent(value: float, target: float) -> float | None:
    if target <= 0:
        return None
    return round((value / target) * 100, 2)


def _food_response(record: FoodLog, user_timezone) -> FoodLogResponse:
    from app.api.time_utils import utc_storage_to_timezone

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
        logged_at=utc_storage_to_timezone(record.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(record.created_at.replace(tzinfo=UTC), user_timezone),
        updated_at=utc_storage_to_timezone(record.updated_at.replace(tzinfo=UTC), user_timezone),
    )


def _exercise_response(record: ExerciseLog, user_timezone) -> ExerciseLogResponse:
    from app.api.time_utils import utc_storage_to_timezone

    return ExerciseLogResponse(
        id=record.id,
        user_id=record.user_id,
        exercise_type=record.exercise_type,
        description=record.description,
        duration_minutes=record.duration_minutes,
        calories_burned=record.calories_burned,
        logged_at=utc_storage_to_timezone(record.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(record.created_at.replace(tzinfo=UTC), user_timezone),
        updated_at=utc_storage_to_timezone(record.updated_at.replace(tzinfo=UTC), user_timezone),
    )
