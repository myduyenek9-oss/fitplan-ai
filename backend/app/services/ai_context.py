from __future__ import annotations

import json
from datetime import UTC, date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationMessage
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.profile import Profile
from app.models.record import BodyMetric, ExerciseLog, FoodLog
from app.models.user import User
from app.schemas.plan import PlanSummary
from app.schemas.record import DailySummaryResponse
from app.services.ai_record_service import build_daily_summary

_FATIGUE_TERMS = ("累", "疲劳", "酸痛", "酸", "力竭", "没力", "乏力", "疼", "痛")

RECENT_MESSAGE_LIMIT = 8
RECENT_CONTEXT_MESSAGE_LIMIT = 6
RECENT_MESSAGE_CONTENT_LIMIT = 500
BOUNDED_CONTEXT_TEXT_LIMIT = 5000


def build_bounded_ai_context_data(
    db: Session,
    *,
    user_id: int,
    message: str,
    today: date,
    system_actions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Every context query is scoped by the authenticated user's id. Never load
    # account-wide rows here: this object is sent to the configured AI provider.
    user = db.get(User, user_id)
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    active_goal = db.scalar(
        select(Goal)
        .where(Goal.user_id == user_id, Goal.is_active.is_(True))
        .order_by(Goal.updated_at.desc(), Goal.id.desc())
        .limit(1)
    )
    current_plan = db.scalar(
        select(Plan)
        .where(Plan.user_id == user_id, Plan.is_active.is_(True))
        .order_by(Plan.updated_at.desc(), Plan.id.desc())
        .limit(1)
    )
    daily_summary = build_daily_summary(db, user_id=user_id, day=today)
    recent_activity = _recent_activity_summary(db, user_id=user_id)
    body_metrics = _body_metric_summary(db, user_id=user_id)
    recent_messages = list(
        db.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.user_id == user_id,
                ConversationMessage.source == "chat",
                ConversationMessage.metadata_json["status"].as_string() == "success",
            )
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(RECENT_MESSAGE_LIMIT)
        )
    )
    return {
        "message": message,
        "today": today.isoformat(),
        "system_actions": system_actions or {},
        "data_semantics": {
            "daily_summary": "actual records logged by this user for today; active records are valid",
            "current_plan": "planned meals and workouts only; not proof that the user consumed or completed them",
        },
        "account": {"username": user.username} if user is not None else None,
        "profile": _profile_summary(profile),
        "goal": _goal_summary(active_goal),
        # Put the selected user's current-day records before the larger plan and
        # conversation sections so the most actionable context is never lost.
        "daily_summary": _bounded_daily_summary(daily_summary),
        "exercise_fatigue": _exercise_fatigue_summary(daily_summary),
        "body_metrics": body_metrics,
        "recent_activity": recent_activity,
        "current_plan": _plan_summary(current_plan),
        "recent_messages": [
            {
                "role": item.role,
                "source": item.source,
                "content": item.content[:RECENT_MESSAGE_CONTENT_LIMIT],
                "created_at": _safe_iso(item.created_at),
            }
            for item in reversed(recent_messages)
        ],
    }


def build_bounded_ai_context_text(
    db: Session,
    *,
    user_id: int,
    message: str,
    today: date,
    system_actions: dict[str, Any] | None = None,
) -> str:
    data = build_bounded_ai_context_data(
        db,
        user_id=user_id,
        message=message,
        today=today,
        system_actions=system_actions,
    )

    # Personal profile, goal, actual records, body metrics and the active plan
    # are the durable source of truth. Conversation history is lower priority:
    # keep only the newest successful chat messages that fit after the important
    # account context has been assembled. Never slice serialized JSON.
    focus_date = _context_focus_date(system_actions) or today
    recent_messages = data.get("recent_messages", [])[-RECENT_CONTEXT_MESSAGE_LIMIT:]
    core_candidates = [
        _context_variant(
            data,
            recent_messages=[],
            recent_activity=_compact_activity(data.get("recent_activity", {}), limit=8),
            body_metrics=data.get("body_metrics", [])[-5:],
            current_plan=_compact_plan(data.get("current_plan"), focus_date=focus_date),
        ),
        _context_variant(
            data,
            recent_messages=[],
            recent_activity=_compact_activity(data.get("recent_activity", {}), limit=5),
            body_metrics=data.get("body_metrics", [])[-3:],
            current_plan=_compact_plan(data.get("current_plan"), focus_date=focus_date),
        ),
        _context_variant(_minimal_context(data, focus_date=focus_date), recent_messages=[]),
        _context_variant(
            _minimal_context(data, focus_date=focus_date, ultra_compact=True),
            recent_messages=[],
        ),
    ]
    for core in core_candidates:
        for keep_count in range(len(recent_messages), -1, -1):
            candidate = _context_variant(
                core,
                recent_messages=recent_messages[-keep_count:] if keep_count else [],
            )
            serialized = json.dumps(candidate, ensure_ascii=False)
            if len(serialized) <= BOUNDED_CONTEXT_TEXT_LIMIT:
                return serialized

    # This last-resort payload still preserves the current request and durable
    # user facts. It should only be reached for unusually large legacy fields.
    final = _context_variant(
        _minimal_context(data, focus_date=focus_date, ultra_compact=True),
        recent_messages=[],
        current_plan=None,
        recent_activity={"food": [], "exercise": []},
        body_metrics=[],
    )
    return json.dumps(final, ensure_ascii=False)


def _context_focus_date(system_actions: dict[str, Any] | None) -> date | None:
    if not system_actions:
        return None
    raw = system_actions.get("target_date") or system_actions.get("source_date")
    if raw is None and isinstance(system_actions.get("plan_adjustment"), dict):
        adjustment = system_actions["plan_adjustment"]
        raw = adjustment.get("target_date") or adjustment.get("source_date")
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _context_variant(data: dict[str, Any], **updates: Any) -> dict[str, Any]:
    variant = dict(data)
    variant.update(updates)
    return variant


def _compact_activity(value: Any, *, limit: int) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {"food": [], "exercise": []}
    result: dict[str, list[dict[str, Any]]] = {}
    for kind in ("food", "exercise"):
        rows = value.get(kind) or []
        result[kind] = [
            {
                key: (str(row.get(key))[:240] if key in {"original_text", "description"} and row.get(key) is not None else row.get(key))
                for key in row
            }
            for row in rows[-limit:]
            if isinstance(row, dict)
        ]
    return result


def _compact_plan(plan: Any, *, focus_date: date | None) -> dict[str, Any] | None:
    if not isinstance(plan, dict):
        return None
    compact_days: list[dict[str, Any]] = []
    for raw_day in plan.get("days", []):
        if not isinstance(raw_day, dict):
            continue
        day_date = raw_day.get("date")
        is_focus = focus_date is not None and day_date == focus_date.isoformat()
        meals: list[dict[str, Any]] = []
        for raw_meal in raw_day.get("meals", []):
            if not isinstance(raw_meal, dict):
                continue
            meal = {
                key: raw_meal.get(key)
                for key in ("name", "meal_type")
            }
            if is_focus:
                meal["calories"] = raw_meal.get("calories")
                meal.update(
                    {
                        key: raw_meal.get(key)
                        for key in ("protein_g", "carb_g", "fat_g")
                    }
                )
                meal["foods"] = [
                    {key: food.get(key) for key in ("name", "amount", "notes")}
                    for food in (raw_meal.get("foods") or [])[:8]
                    if isinstance(food, dict)
                ]
            meals.append(meal)
        raw_training = raw_day.get("training_instruction") or {}
        training = {
            key: raw_training.get(key)
            for key in ("kind", "title")
        }
        if is_focus:
            training.update(
                {
                    key: raw_training.get(key)
                    for key in ("duration_minutes", "split", "focus")
                }
            )
            training.update(
                {
                    "instructions": str(raw_training.get("instructions") or "")[:600],
                    "warmup": str(raw_training.get("warmup") or "")[:240] or None,
                    "cooldown": str(raw_training.get("cooldown") or "")[:240] or None,
                    "exercises": [
                        {key: exercise.get(key) for key in ("name", "sets", "reps", "rest_seconds", "notes")}
                        for exercise in (raw_training.get("exercises") or [])[:8]
                        if isinstance(exercise, dict)
                    ],
                }
            )
        if is_focus:
            compact_days.append(
                {
                    "date": day_date,
                    "calorie_target": raw_day.get("calorie_target"),
                    "meals": meals,
                    "training_instruction": training,
                }
            )
        else:
            compact_days.append(
                {
                    "date": day_date,
                    "meals": meals,
                    "training_instruction": training,
                }
            )
    return {
        key: plan.get(key)
        for key in ("id", "title", "start_date", "end_date", "is_active")
    } | {"days": compact_days}


def _minimal_context(data: dict[str, Any], *, focus_date: date | None, ultra_compact: bool = False) -> dict[str, Any]:
    daily = data.get("daily_summary") or {}
    daily_records = {
        "date": daily.get("date"),
        "food_totals": daily.get("food_totals"),
        "exercise_totals": daily.get("exercise_totals"),
        "remaining_calories": daily.get("remaining_calories"),
        "food_records": [],
        "exercise_records": [],
    }
    record_limit = 2 if ultra_compact else 4
    text_limit = 120 if ultra_compact else 240
    for kind, keys in (
        ("food_records", ("id", "original_text", "meal_type", "calories", "protein_g", "carb_g", "fat_g", "logged_at", "status")),
        ("exercise_records", ("id", "original_text", "exercise_type", "description", "duration_minutes", "calories_burned", "logged_at")),
    ):
        for row in (daily.get(kind) or [])[-record_limit:]:
            if isinstance(row, dict):
                item = {key: row.get(key) for key in keys}
                for key in ("original_text", "description"):
                    if item.get(key) is not None:
                        item[key] = str(item[key])[:text_limit]
                daily_records[kind].append(item)

    result = {
        "message": str(data.get("message") or "")[:2000 if not ultra_compact else 1500],
        "today": data.get("today"),
        "system_actions": data.get("system_actions") or {},
        "data_semantics": data.get("data_semantics"),
        "account": data.get("account"),
        "profile": data.get("profile"),
        "goal": data.get("goal"),
        "daily_summary": daily_records,
        "exercise_fatigue": data.get("exercise_fatigue"),
        "current_plan": _compact_plan(
            data.get("current_plan"),
            focus_date=None if ultra_compact else focus_date,
        ),
        "recent_messages": [
            {
                "role": row.get("role"),
                "source": row.get("source"),
                "content": str(row.get("content") or "")[:text_limit],
                "created_at": row.get("created_at"),
            }
            for row in (data.get("recent_messages") or [])[-(2 if ultra_compact else 4):]
            if isinstance(row, dict)
        ],
    }
    if not ultra_compact:
        result["body_metrics"] = (data.get("body_metrics") or [])[-5:]
        result["recent_activity"] = _compact_activity(data.get("recent_activity", {}), limit=5)
    return result


def _profile_summary(profile: Profile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "display_name": profile.display_name,
        "sex": profile.sex,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "height_cm": profile.height_cm,
        "timezone": profile.timezone,
    }


def _goal_summary(goal: Goal | None) -> dict[str, Any] | None:
    if goal is None:
        return None
    return {
        "goal_type": goal.goal_type,
        "daily_calories": goal.daily_calories,
        "protein_g": goal.protein_g,
        "carb_g": goal.carb_g,
        "fat_g": goal.fat_g,
        "activity_level": goal.activity_level,
        "target_weight_kg": goal.target_weight_kg,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
    }


def _plan_summary(plan: Plan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return PlanSummary.from_orm_plan(plan).model_dump(mode="json")


def _safe_iso(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _bounded_daily_summary(summary: DailySummaryResponse) -> dict[str, Any]:
    data = summary.model_dump(mode="json")
    # Do not pass parsed_content/source metadata wholesale: it can crowd out the
    # actual records in a bounded prompt. These are the fields the coach needs.
    return {
        "date": data.get("date"),
        "goal": data.get("goal"),
        "food_totals": data.get("food_totals"),
        "exercise_totals": data.get("exercise_totals"),
        "remaining_calories": data.get("remaining_calories"),
        "food_records": [
            {key: record.get(key) for key in (
                "id", "original_text", "meal_type", "calories", "protein_g",
                "carb_g", "fat_g", "logged_at", "status"
            )}
            for record in data.get("food_records", [])[:8]
        ],
        "exercise_records": [
            {key: record.get(key) for key in (
                "id", "original_text", "exercise_type", "description",
                "duration_minutes", "calories_burned", "logged_at"
            )}
            for record in data.get("exercise_records", [])[:8]
        ],
    }


def _recent_activity_summary(db: Session, *, user_id: int) -> dict[str, list[dict[str, Any]]]:
    foods = list(db.scalars(
        select(FoodLog)
        .where(FoodLog.user_id == user_id, FoodLog.status == "active")
        .order_by(FoodLog.logged_at.desc(), FoodLog.id.desc())
        .limit(20)
    ))
    exercises = list(db.scalars(
        select(ExerciseLog)
        .where(ExerciseLog.user_id == user_id)
        .order_by(ExerciseLog.logged_at.desc(), ExerciseLog.id.desc())
        .limit(20)
    ))
    return {
        "food": [
            {
                "id": item.id,
                "original_text": item.original_text,
                "meal_type": item.meal_type,
                "calories": item.calories,
                "protein_g": item.protein_g,
                "carb_g": item.carb_g,
                "fat_g": item.fat_g,
                "logged_at": _safe_iso(item.logged_at),
            }
            for item in reversed(foods)
        ],
        "exercise": [
            {
                "id": item.id,
                "original_text": item.original_text,
                "exercise_type": item.exercise_type,
                "description": item.description,
                "duration_minutes": item.duration_minutes,
                "calories_burned": item.calories_burned,
                "logged_at": _safe_iso(item.logged_at),
            }
            for item in reversed(exercises)
        ],
    }


def _body_metric_summary(db: Session, *, user_id: int) -> list[dict[str, Any]]:
    metrics = list(db.scalars(
        select(BodyMetric)
        .where(BodyMetric.user_id == user_id)
        .order_by(BodyMetric.logged_at.desc(), BodyMetric.id.desc())
        .limit(10)
    ))
    return [
        {
            "weight_kg": item.weight_kg,
            "body_fat_percent": item.body_fat_percent,
            "waist_cm": item.waist_cm,
            "chest_cm": item.chest_cm,
            "hip_cm": item.hip_cm,
            "notes": item.notes,
            "logged_at": _safe_iso(item.logged_at),
        }
        for item in reversed(metrics)
    ]


def _exercise_fatigue_summary(summary: DailySummaryResponse) -> dict[str, Any]:
    recent_exercises = []
    fatigue_terms: set[str] = set()
    for record in summary.exercise_records[:5]:
        combined = " ".join(filter(None, [record.original_text, record.description]))
        fatigue_terms.update(term for term in _FATIGUE_TERMS if term in combined)
        recent_exercises.append(
            {
                "exercise_type": record.exercise_type,
                "description": record.description,
                "original_text": record.original_text,
                "duration_minutes": record.duration_minutes,
                "calories_burned": record.calories_burned,
                "logged_at": record.logged_at.isoformat(),
            }
        )
    return {
        "record_count": len(summary.exercise_records),
        "duration_minutes": summary.exercise_totals.duration_minutes,
        "calories_burned": summary.exercise_totals.calories_burned,
        "reported_fatigue": bool(fatigue_terms),
        "fatigue_terms": sorted(fatigue_terms),
        "recent_exercises": recent_exercises,
    }
