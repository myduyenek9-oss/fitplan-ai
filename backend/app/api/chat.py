from __future__ import annotations

import json
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.ai import get_ai_client
from app.api.deps import get_current_user, get_db
from app.api.time_utils import get_user_timezone, utc_storage_to_timezone
from app.models.conversation import ConversationMessage
from app.models.record import ExerciseLog, FoodLog
from app.models.user import User
from app.schemas.plan import MealPlan
from app.schemas.chat import (
    ChatHistoryDeleteRequest,
    ChatHistoryDeleteResponse,
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    PlanAdjustmentResponse,
)
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_context import build_bounded_ai_context_data, build_bounded_ai_context_text
from app.services.ai_prompts import (
    CHAT_SYSTEM_PROMPT,
    MEAL_REPLACEMENT_SYSTEM_PROMPT,
    EXERCISE_PARSE_SYSTEM_PROMPT,
    MIXED_RECORD_PARSE_SYSTEM_PROMPT,
)
from app.services.ai_record_service import (
    _exercise_response,
    _food_response,
    _resolve_recorded_at,
    build_daily_summary,
)
from app.services.ai_schemas import ParsedExerciseResult, ParsedMixedRecordResult

from app.services.plan_adjustment import (
    detect_meal_replacement_request,
    detect_postpone_training_request,
)
from app.services.plan_service import PlanService
from app.services.record_detection import (
    looks_like_completed_exercise,
    looks_like_mixed_completed_records,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


async def _try_record_mixed_completed_records(
    db: Session,
    *,
    ai_client: AiClient,
    user_id: int,
    text: str,
    today: date,
) -> tuple[FoodLog | None, ExerciseLog | None]:
    if not looks_like_mixed_completed_records(text):
        return None, None
    try:
        raw_result = await ai_client.chat_json(
            system=MIXED_RECORD_PARSE_SYSTEM_PROMPT,
            user=json.dumps(
                {
                    "source_text": text,
                    "today": today.isoformat(),
                    "instructions": "Split completed diet and exercise into separate records. Return JSON only.",
                },
                ensure_ascii=False,
            ),
        )
        parsed = ParsedMixedRecordResult.model_validate(raw_result)
    except (AiProviderError, ValidationError, TypeError, ValueError):
        # Automatic splitting must never block the normal coaching reply.
        return None, None

    user_timezone = get_user_timezone(db, user_id)
    food_record: FoodLog | None = None
    exercise_record: ExerciseLog | None = None

    if parsed.diet is not None:
        food_record = FoodLog(
            user_id=user_id,
            original_text=parsed.diet.description,
            parsed_content={
                **parsed.diet.model_dump(mode="json"),
                "estimated": True,
                "source": "mixed_chat",
                "source_text": text,
            },
            meal_type=parsed.diet.meal_type,
            calories=round(parsed.diet.calories, 2),
            protein_g=round(parsed.diet.protein_g, 2),
            carb_g=round(parsed.diet.carb_g, 2),
            fat_g=round(parsed.diet.fat_g, 2),
            status="active",
            logged_at=_resolve_recorded_at(
                text=parsed.diet.description,
                parsed_logged_at=parsed.diet.logged_at,
                day=today,
                user_timezone=user_timezone,
            ),
        )
        db.add(food_record)

    if parsed.exercise is not None:
        exercise_text = parsed.exercise.description or parsed.exercise.exercise_type
        exercise_record = ExerciseLog(
            user_id=user_id,
            original_text=exercise_text,
            exercise_type=parsed.exercise.exercise_type,
            description=parsed.exercise.description,
            duration_minutes=round(parsed.exercise.duration_minutes, 2),
            calories_burned=round(parsed.exercise.calories_burned, 2),
            logged_at=_resolve_recorded_at(
                text=exercise_text,
                parsed_logged_at=parsed.exercise.logged_at,
                day=today,
                user_timezone=user_timezone,
            ),
        )
        db.add(exercise_record)

    db.flush()
    return food_record, exercise_record


async def _try_record_completed_exercise(
    db: Session,
    *,
    ai_client: AiClient,
    user_id: int,
    text: str,
    today: date,
) -> ExerciseLog | None:
    if not looks_like_completed_exercise(text):
        return None
    try:
        raw_result = await ai_client.chat_json(
            system=EXERCISE_PARSE_SYSTEM_PROMPT,
            user=json.dumps(
                {
                    "source_text": text,
                    "today": today.isoformat(),
                    "instructions": "Parse only the exercise already completed by the user. Return JSON only.",
                },
                ensure_ascii=False,
            ),
        )
        parsed = ParsedExerciseResult.model_validate(raw_result)
    except (AiProviderError, ValidationError, TypeError, ValueError):
        # Exercise auto-recording is an enhancement; a parsing failure must not block normal coaching chat.
        return None

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
    return record


def _day_label(value: date) -> str:
    return f"{value.month}\u6708{value.day}\u65e5"


def _meal_label(value: str) -> str:
    return {
        "breakfast": "早餐",
        "lunch": "午餐",
        "snack": "加餐",
        "dinner": "晚餐",
    }.get(value, value)



def _apply_requested_plan_adjustment(
    db: Session,
    *,
    user_id: int,
    message: str,
    today: date,
) -> PlanAdjustmentResponse | None:
    source_date = detect_postpone_training_request(message, today)
    if source_date is None:
        return None

    service = PlanService()
    plan = service.get_current_plan(db, user_id=user_id)
    if plan is None:
        return PlanAdjustmentResponse(
            action="postpone_training",
            status="not_applicable",
            source_date=source_date,
            message="\u76ee\u524d\u6ca1\u6709\u6b63\u5728\u6267\u884c\u7684 7 \u5929\u8ba1\u5212\uff0c\u8bf7\u5148\u751f\u6210\u4e00\u5468\u8ba1\u5212\u3002",
        )

    try:
        updated_plan = service.postpone_training(
            db,
            user_id=user_id,
            plan_id=plan.id,
            day=source_date,
        )
    except ValueError as exc:
        reason = str(exc)
        if reason == "plan day not found":
            adjustment_message = (
                f"{_day_label(source_date)}\u4e0d\u5728\u5f53\u524d 7 \u5929\u8ba1\u5212\u8303\u56f4\u5185\uff0c"
                "\u6240\u4ee5\u8fd8\u6ca1\u6709\u4fee\u6539\u8ba1\u5212\u3002"
            )
        elif reason == "only workout days can be postponed":
            adjustment_message = (
                f"{_day_label(source_date)}\u539f\u672c\u5c31\u662f\u6062\u590d\u65e5\uff0c"
                "\u6ca1\u6709\u9700\u8981\u987a\u5ef6\u7684\u8bad\u7ec3\u3002"
            )
        elif reason == "no recovery day available":
            adjustment_message = (
                "\u5f53\u524d\u8ba1\u5212\u540e\u9762\u6ca1\u6709\u53ef\u7528\u7684\u6062\u590d\u65e5\uff0c"
                "\u4e3a\u907f\u514d\u8986\u76d6\u5df2\u6709\u5b89\u6392\uff0c\u8fd9\u6b21\u6ca1\u6709\u81ea\u52a8\u4fee\u6539\u3002"
            )
        else:
            adjustment_message = "\u8fd9\u6b21\u8bad\u7ec3\u987a\u5ef6\u6ca1\u6709\u6210\u529f\uff0c\u8ba1\u5212\u4fdd\u6301\u4e0d\u53d8\u3002"
        return PlanAdjustmentResponse(
            action="postpone_training",
            status="not_applicable",
            plan_id=plan.id,
            source_date=source_date,
            message=adjustment_message,
        )

    if updated_plan is None:
        return PlanAdjustmentResponse(
            action="postpone_training",
            status="failed",
            plan_id=plan.id,
            source_date=source_date,
            message="\u6ca1\u6709\u627e\u5230\u53ef\u4fee\u6539\u7684\u8ba1\u5212\uff0c\u8fd9\u6b21\u672a\u66f4\u65b0\u3002",
        )

    target_date = source_date + timedelta(days=1)
    return PlanAdjustmentResponse(
        action="postpone_training",
        status="applied",
        plan_id=updated_plan.id,
        source_date=source_date,
        target_date=target_date,
        message=(
            f"\u5df2\u5c06{_day_label(source_date)}\u7684\u8bad\u7ec3\u987a\u5ef6\u5230"
            f"{_day_label(target_date)}\uff0c\u539f\u65e5\u671f\u5df2\u6539\u4e3a\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d\uff0c"
            "\u540e\u7eed\u8bad\u7ec3\u4e5f\u5df2\u4f9d\u6b21\u987a\u5ef6\u5e76\u4fdd\u5b58\u3002"
        ),
    )


async def _apply_requested_meal_replacement(
    db: Session,
    *,
    ai_client: AiClient,
    user_id: int,
    message: str,
    today: date,
) -> PlanAdjustmentResponse | None:
    request = detect_meal_replacement_request(message, today)
    if request is None:
        return None
    target_date, meal_type = request
    service = PlanService()
    plan = service.get_current_plan(db, user_id=user_id)
    if plan is None:
        return PlanAdjustmentResponse(
            action="replace_meal",
            status="not_applicable",
            source_date=target_date,
            meal_type=meal_type,
            message="目前没有正在执行的 7 天计划，请先生成一周计划。",
        )

    target_day = next((item for item in plan.days if item.date == target_date), None)
    if target_day is None:
        return PlanAdjustmentResponse(
            action="replace_meal",
            status="not_applicable",
            plan_id=plan.id,
            source_date=target_date,
            meal_type=meal_type,
            message=f"{_day_label(target_date)}不在当前 7 天计划范围内，这次没有修改。",
        )
    current_meal = next(
        (meal for meal in target_day.meals if meal.meal_type == meal_type),
        None,
    )
    if current_meal is None:
        return PlanAdjustmentResponse(
            action="replace_meal",
            status="not_applicable",
            plan_id=plan.id,
            source_date=target_date,
            meal_type=meal_type,
            message=f"{_day_label(target_date)}没有找到可替换的{_meal_label(meal_type)}，这次没有修改。",
        )

    context = build_bounded_ai_context_data(
        db,
        user_id=user_id,
        message=message,
        today=today,
        system_actions={"requested_action": "replace_meal", "meal_type": meal_type, "target_date": target_date.isoformat()},
    )
    target_day_context = {
        "date": target_day.date.isoformat(),
        "calorie_target": target_day.calorie_target,
        "meals": [meal.model_dump(mode="json") for meal in target_day.meals],
        "training_instruction": target_day.training_instruction.model_dump(mode="json"),
    }
    replacement_prompt = json.dumps(
        {
            "request": message,
            "target_date": target_date.isoformat(),
            "target_meal_type": meal_type,
            "current_meal": current_meal.model_dump(mode="json"),
            "current_day_plan": target_day_context,
            "user_profile": context.get("profile"),
            "user_goal": context.get("goal"),
            "today_records": context.get("daily_summary"),
            "recent_activity": context.get("recent_activity"),
            "instructions": "Only replace this meal. Keep every other meal, workout, and date unchanged.",
        },
        ensure_ascii=False,
    )
    try:
        raw_result = await ai_client.chat_json(
            system=MEAL_REPLACEMENT_SYSTEM_PROMPT,
            user=replacement_prompt,
        )
        replacement_payload = raw_result.get("meal", raw_result)
        replacement = MealPlan.model_validate({**replacement_payload, "meal_type": meal_type})
        if len(replacement.foods) < 3:
            raise ValueError("replacement meal must contain concrete foods")
        updated = service.replace_meal(
            db,
            user_id=user_id,
            plan_id=plan.id,
            day=target_date,
            meal_type=meal_type,
            replacement=replacement,
        )
        if updated is None:
            raise ValueError("plan not found")
        _, previous = updated
    except (AiProviderError, ValidationError, TypeError, ValueError):
        return PlanAdjustmentResponse(
            action="replace_meal",
            status="not_applicable",
            plan_id=plan.id,
            source_date=target_date,
            meal_type=meal_type,
            previous_meal_name=current_meal.name,
            message="AI 暂时没有返回可用的替代餐，原计划保持不变。请检查 AI 配置后再试。",
        )

    return PlanAdjustmentResponse(
        action="replace_meal",
        status="applied",
        plan_id=plan.id,
        source_date=target_date,
        target_date=target_date,
        meal_type=meal_type,
        previous_meal_name=previous.name,
        updated_meal_name=replacement.name,
        message=(
            f"已为你更新{_day_label(target_date)}的{_meal_label(meal_type)}："
            f"{previous.name} 已替换为 {replacement.name}，其他餐次、训练和日期保持不变。"
        ),
    )


def _history_message(message: ConversationMessage, *, user_timezone: ZoneInfo) -> ChatHistoryMessage:
    raw_adjustment = (message.metadata_json or {}).get("plan_adjustment")
    plan_adjustment = None
    if raw_adjustment is not None:
        try:
            plan_adjustment = PlanAdjustmentResponse.model_validate(raw_adjustment)
        except ValidationError:
            plan_adjustment = None
    return ChatHistoryMessage(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=utc_storage_to_timezone(message.created_at, user_timezone),
        plan_adjustment=plan_adjustment,
    )


@router.get("/history", response_model=list[ChatHistoryMessage])
def history(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatHistoryMessage]:
    messages = list(
        db.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.user_id == current_user.id,
                ConversationMessage.source == "chat",
                ConversationMessage.metadata_json["status"].as_string() == "success",
            )
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(limit)
        )
    )
    user_timezone = get_user_timezone(db, current_user.id)
    return [_history_message(message, user_timezone=user_timezone) for message in reversed(messages)]


@router.post("/history/delete", response_model=ChatHistoryDeleteResponse)
def delete_history_messages(
    payload: ChatHistoryDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatHistoryDeleteResponse:
    message_ids = sorted(set(payload.message_ids))
    owned_ids = list(
        db.scalars(
            select(ConversationMessage.id).where(
                ConversationMessage.user_id == current_user.id,
                ConversationMessage.source == "chat",
                ConversationMessage.id.in_(message_ids),
            )
        )
    )
    if owned_ids:
        db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.user_id == current_user.id,
                ConversationMessage.source == "chat",
                ConversationMessage.id.in_(owned_ids),
            )
        )
        db.commit()
    return ChatHistoryDeleteResponse(deleted_count=len(owned_ids))


@router.delete("/history", response_model=ChatHistoryDeleteResponse)
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatHistoryDeleteResponse:
    message_ids = list(
        db.scalars(
            select(ConversationMessage.id).where(
                ConversationMessage.user_id == current_user.id,
                ConversationMessage.source == "chat",
            )
        )
    )
    if message_ids:
        db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.user_id == current_user.id,
                ConversationMessage.source == "chat",
            )
        )
        db.commit()
    return ChatHistoryDeleteResponse(deleted_count=len(message_ids))


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AiClient = Depends(get_ai_client),
) -> ChatResponse:
    today = payload.today or date.today()
    user_message = ConversationMessage(
        user_id=current_user.id,
        role="user",
        content=payload.message,
        source="chat",
        metadata_json={"status": "pending"},
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    plan_adjustment = _apply_requested_plan_adjustment(
        db,
        user_id=current_user.id,
        message=payload.message,
        today=today,
    )
    if plan_adjustment is None:
        plan_adjustment = await _apply_requested_meal_replacement(
            db,
            ai_client=ai_client,
            user_id=current_user.id,
            message=payload.message,
            today=today,
        )

    recorded_food, recorded_exercise = await _try_record_mixed_completed_records(
        db,
        ai_client=ai_client,
        user_id=current_user.id,
        text=payload.message,
        today=today,
    )
    if recorded_food is None and recorded_exercise is None:
        recorded_exercise = await _try_record_completed_exercise(
            db,
            ai_client=ai_client,
            user_id=current_user.id,
            text=payload.message,
            today=today,
        )
    try:
        reply = await ai_client.chat_text(
            system=CHAT_SYSTEM_PROMPT,
            user=build_bounded_ai_context_text(
                db,
                user_id=current_user.id,
                message=payload.message,
                today=today,
                system_actions=(
                    {"plan_adjustment": plan_adjustment.model_dump(mode="json")}
                    if plan_adjustment is not None
                    else None
                ),
            ),
        )
    except AiProviderError as exc:
        if plan_adjustment is None:
            user_message.metadata_json = {"status": "failed", "reason": str(exc)}
            db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        reply = plan_adjustment.message

    metadata = {"status": "success", "reply_to": user_message.id}
    user_metadata = {"status": "success"}
    if plan_adjustment is not None:
        adjustment_payload = plan_adjustment.model_dump(mode="json")
        metadata["plan_adjustment"] = adjustment_payload
    saved_records: dict[str, int] = {}
    if recorded_food is not None:
        saved_records["food"] = recorded_food.id
    if recorded_exercise is not None:
        saved_records["exercise"] = recorded_exercise.id
    if saved_records:
        metadata.update({"record_ids": saved_records, "record_types": list(saved_records)})
        user_metadata.update({"record_ids": saved_records, "record_types": list(saved_records)})

    assistant_message = ConversationMessage(
        user_id=current_user.id,
        role="assistant",
        content=reply,
        source="chat",
        metadata_json=metadata,
    )
    user_message.metadata_json = user_metadata
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    food_response = None
    exercise_response = None
    daily_summary = None
    user_timezone = get_user_timezone(db, current_user.id)
    if recorded_food is not None or recorded_exercise is not None:
        if recorded_food is not None:
            db.refresh(recorded_food)
            food_response = _food_response(recorded_food, user_timezone)
        if recorded_exercise is not None:
            db.refresh(recorded_exercise)
            exercise_response = _exercise_response(recorded_exercise, user_timezone)
        daily_summary = build_daily_summary(db, user_id=current_user.id, day=today)

    return ChatResponse(
        reply=reply,
        conversation_id=assistant_message.id,
        user_message_id=user_message.id,
        user_created_at=utc_storage_to_timezone(user_message.created_at, user_timezone),
        assistant_created_at=utc_storage_to_timezone(assistant_message.created_at, user_timezone),
        recorded_food=food_response,
        recorded_exercise=exercise_response,
        daily_summary=daily_summary,
        plan_adjustment=plan_adjustment,
    )
