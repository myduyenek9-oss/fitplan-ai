from __future__ import annotations

import json
from datetime import UTC, date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.ai import get_ai_client
from app.api.deps import get_current_user, get_db
from app.models.conversation import ConversationMessage
from app.models.plan import Plan
from app.models.profile import Profile
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.plan import PlanSummary
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_prompts import CHAT_SYSTEM_PROMPT
from app.services.ai_record_service import build_daily_summary

router = APIRouter(prefix="/api/ai", tags=["ai"])


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
    try:
        reply = await ai_client.chat_text(
            system=CHAT_SYSTEM_PROMPT,
            user=_build_bounded_context(db, user_id=current_user.id, message=payload.message, today=today),
        )
    except AiProviderError as exc:
        user_message.metadata_json = {"status": "failed", "reason": str(exc)}
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    assistant_message = ConversationMessage(
        user_id=current_user.id,
        role="assistant",
        content=reply,
        source="chat",
        metadata_json={"status": "success", "reply_to": user_message.id},
    )
    user_message.metadata_json = {"status": "success"}
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return ChatResponse(reply=reply, conversation_id=assistant_message.id)


def _build_bounded_context(db: Session, *, user_id: int, message: str, today: date) -> str:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    current_plan = db.scalar(
        select(Plan)
        .where(Plan.user_id == user_id, Plan.is_active.is_(True))
        .order_by(Plan.updated_at.desc(), Plan.id.desc())
        .limit(1)
    )
    recent_messages = list(
        db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(10)
        )
    )
    context: dict[str, Any] = {
        "message": message,
        "today": today.isoformat(),
        "profile": _profile_summary(profile),
        "current_plan": _plan_summary(current_plan),
        "daily_summary": build_daily_summary(db, user_id=user_id, day=today).model_dump(mode="json"),
        "recent_messages": [
            {
                "role": item.role,
                "source": item.source,
                "content": item.content[:500],
                "created_at": _safe_iso(item.created_at),
            }
            for item in reversed(recent_messages)
        ],
    }
    return json.dumps(context, ensure_ascii=False)[:5000]


def _profile_summary(profile: Profile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "sex": profile.sex,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "height_cm": profile.height_cm,
        "timezone": profile.timezone,
    }


def _plan_summary(plan: Plan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return PlanSummary.from_orm_plan(plan).model_dump(mode="json")


def _safe_iso(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
