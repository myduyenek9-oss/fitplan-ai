from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

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
    CalorieCalculation,
    DailyGoalSnapshot,
    DailySummaryResponse,
    ExerciseLogResponse,
    ExerciseTotals,
    FoodLogResponse,
    FoodTotals,
    MacroCompletionPercentages,
)
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_prompts import (
    EXERCISE_PARSE_SYSTEM_PROMPT,
    FOOD_PARSE_SYSTEM_PROMPT,
    MIXED_RECORD_PARSE_SYSTEM_PROMPT,
)
from app.services.ai_schemas import ParsedExerciseResult, ParsedFoodResult, ParsedMixedRecordResult
from app.services.record_detection import looks_like_mixed_completed_records


_EXPLICIT_MINUTE_PATTERN = re.compile(
    r"(?:\d{1,2}\s*[:\uFF1A]\s*\d{1,2}|(?:\d{1,2}|[\u96F6\u3007\u4E00\u4E8C\u4E24\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341]{1,3})\s*[\u70B9\u65F6]\s*(?:(?:\d{1,2}|[\u96F6\u3007\u4E00\u4E8C\u4E24\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341]{1,3})\s*\u5206?|\u534A|\u4E00\u523B|\u4E09\u523B))"
)
_EXPLICIT_TIME_OF_DAY_PATTERN = re.compile(r"\u65e9\u4e0a|\u4e0a\u5348|\u4e2d\u5348|\u4e0b\u5348|\u508d\u665a|\u665a\u4e0a|\u591c\u91cc|\u65e9\u9910|\u5348\u9910|\u665a\u9910")


class AiRecordError(RuntimeError):
    """Raised when a natural-language record cannot be safely created."""


def _estimate_range(value: float, confidence: float | None) -> tuple[float, float]:
    """Return a transparent estimate interval without changing the stored midpoint."""
    confidence = confidence if confidence is not None else 0.6
    margin = 0.10 if confidence >= 0.8 else 0.20 if confidence >= 0.6 else 0.30
    return (round(max(0, value * (1 - margin)), 2), round(value * (1 + margin), 2))


@dataclass(frozen=True)
class FoodNaturalLanguageResult:
    record: FoodLogResponse
    recorded_exercise: ExerciseLogResponse | None
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
        is_mixed_record = looks_like_mixed_completed_records(text)
        try:
            if is_mixed_record:
                raw_result = await self.ai_client.chat_json(
                    system=MIXED_RECORD_PARSE_SYSTEM_PROMPT,
                    user=json.dumps(
                        {
                            "source_text": text,
                            "today": today.isoformat(),
                            "instructions": (
                                "Split the completed diet and exercise into separate records. "
                                "Both diet and exercise must be returned. Return JSON only."
                            ),
                        },
                        ensure_ascii=False,
                    ),
                )
                mixed = ParsedMixedRecordResult.model_validate(raw_result)
                if mixed.diet is None or mixed.exercise is None:
                    raise ValueError("mixed quick record must contain both diet and exercise")
                parsed = mixed.diet
                parsed_exercise = mixed.exercise
                food_text = mixed.diet.description
            else:
                raw_result = await self.ai_client.chat_json(
                    system=FOOD_PARSE_SYSTEM_PROMPT,
                    user=self._record_user_prompt(text=text, today=today),
                )
                parsed = ParsedFoodResult.model_validate(raw_result)
                parsed_exercise = None
                food_text = text
        except AiProviderError as exc:
            self._mark_failed(db, user_message, reason=str(exc))
            raise AiRecordError(str(exc)) from exc
        except (ValidationError, TypeError, ValueError) as exc:
            reason = "AI returned invalid mixed record data" if is_mixed_record else "AI returned invalid food data"
            self._mark_failed(db, user_message, reason=reason)
            raise AiRecordError(reason) from exc

        user_timezone = get_user_timezone(db, user_id)
        record = FoodLog(
            user_id=user_id,
            original_text=food_text,
            parsed_content={
                **parsed.model_dump(mode="json"),
                "estimated": True,
                "estimate_range": {
                    "calories_min": _estimate_range(parsed.calories, parsed.confidence)[0],
                    "calories_max": _estimate_range(parsed.calories, parsed.confidence)[1],
                },
                "source": "mixed_quick_record" if parsed_exercise is not None else "ai",
                **({"source_text": text} if parsed_exercise is not None else {}),
            },
            meal_type=parsed.meal_type,
            calories=round(parsed.calories, 2),
            protein_g=round(parsed.protein_g, 2),
            carb_g=round(parsed.carb_g, 2),
            fat_g=round(parsed.fat_g, 2),
            status="active",
            logged_at=_resolve_recorded_at(
                text=food_text,
                parsed_logged_at=parsed.logged_at,
                day=today,
                user_timezone=user_timezone,
            ),
        )
        db.add(record)

        exercise_record: ExerciseLog | None = None
        if parsed_exercise is not None:
            exercise_text = parsed_exercise.description or parsed_exercise.exercise_type
            exercise_record = ExerciseLog(
                user_id=user_id,
                original_text=exercise_text,
                exercise_type=parsed_exercise.exercise_type,
                description=parsed_exercise.description,
                duration_minutes=round(parsed_exercise.duration_minutes, 2),
                calories_burned=round(parsed_exercise.calories_burned, 2),
                logged_at=_resolve_recorded_at(
                    text=exercise_text,
                    parsed_logged_at=parsed_exercise.logged_at,
                    day=today,
                    user_timezone=user_timezone,
                ),
            )
            db.add(exercise_record)

        db.flush()
        record_ids = {"food": record.id}
        if exercise_record is not None:
            record_ids["exercise"] = exercise_record.id
        metadata = {
            "status": "success",
            "record_ids": record_ids,
            "record_types": list(record_ids),
        }
        if exercise_record is None:
            metadata.update({"record_id": record.id, "record_type": "food"})

        suggestions = [parsed.adjustment_suggestion]
        if parsed_exercise is not None and parsed_exercise.adjustment_suggestion not in suggestions:
            suggestions.append(parsed_exercise.adjustment_suggestion)
        adjustment_suggestion = "\n".join(suggestions)
        assistant_message = ConversationMessage(
            user_id=user_id,
            role="assistant",
            content=adjustment_suggestion,
            source="food_natural_language",
            metadata_json=metadata,
        )
        user_message.metadata_json = metadata
        db.add(assistant_message)
        db.commit()
        db.refresh(record)
        if exercise_record is not None:
            db.refresh(exercise_record)
        db.refresh(assistant_message)
        return FoodNaturalLanguageResult(
            record=_food_response(record, user_timezone),
            recorded_exercise=(
                _exercise_response(exercise_record, user_timezone)
                if exercise_record is not None
                else None
            ),
            daily_summary=build_daily_summary(db, user_id=user_id, day=today),
            adjustment_suggestion=adjustment_suggestion,
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
            original_text=text,
            exercise_type=parsed.exercise_type,
            description=parsed.description,
            duration_minutes=round(parsed.duration_minutes, 2),
            calories_burned=round(parsed.calories_burned, 2),
            logged_at=_resolve_recorded_at(
                text=text,
                parsed_logged_at=parsed.logged_at,
                day=today,
                user_timezone=user_timezone,
            ),
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


def _resolve_recorded_at(
    *,
    text: str,
    parsed_logged_at: datetime,
    day: date,
    user_timezone,
    now: datetime | None = None,
) -> datetime:
    """Use an explicitly stated minute, otherwise keep the exact submission minute."""
    if _EXPLICIT_MINUTE_PATTERN.search(text) or _EXPLICIT_TIME_OF_DAY_PATTERN.search(text):
        return to_utc_storage(parsed_logged_at)

    local_now = (now or datetime.now(user_timezone)).astimezone(user_timezone)
    submitted_at = local_now.replace(
        year=day.year,
        month=day.month,
        day=day.day,
        microsecond=0,
    )
    return to_utc_storage(submitted_at)


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
        calorie_calculation=CalorieCalculation(
            formula="\u76ee\u6807\u70ed\u91cf - \u5df2\u6444\u5165\u98df\u7269\u70ed\u91cf + \u8fd0\u52a8\u6d88\u8017",
            exercise_included_fully=True,
            explanation="\u4eca\u5929\u8bb0\u5f55\u7684\u8fd0\u52a8\u6d88\u8017\u4f1a\u5168\u90e8\u8ba1\u5165\u53ef\u6444\u5165\u989d\u5ea6\uff1b\u8fd0\u52a8\u4f30\u7b97\u5b58\u5728\u8bef\u5dee\u65f6\uff0c\u8bf7\u628a\u7ed3\u679c\u4f5c\u4e3a\u53c2\u8003\uff0c\u4e0d\u8981\u4e3a\u4e86\u5403\u56de\u70ed\u91cf\u800c\u5f3a\u884c\u52a0\u9910\u3002",
        ),
        macro_completion_percentages=macro_percentages,
        food_status_counts=status_counts,
        food_records=[
            _food_response(record, user_timezone)
            for record in sorted(active_food_logs, key=lambda item: (item.logged_at, item.id))
        ],
        exercise_records=[
            _exercise_response(record, user_timezone)
            for record in sorted(exercise_logs, key=lambda item: (item.logged_at, item.id))
        ],
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
        calories_min=(record.parsed_content.get("estimate_range", {}) or {}).get("calories_min"),
        calories_max=(record.parsed_content.get("estimate_range", {}) or {}).get("calories_max"),
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
        original_text=record.original_text,
        exercise_type=record.exercise_type,
        description=record.description,
        duration_minutes=record.duration_minutes,
        calories_burned=record.calories_burned,
        calories_burned_min=round(record.calories_burned * 0.8, 2),
        calories_burned_max=round(record.calories_burned * 1.2, 2),
        logged_at=utc_storage_to_timezone(record.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(record.created_at.replace(tzinfo=UTC), user_timezone),
        updated_at=utc_storage_to_timezone(record.updated_at.replace(tzinfo=UTC), user_timezone),
    )
