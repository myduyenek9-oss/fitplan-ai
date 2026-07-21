from __future__ import annotations

import json
from datetime import UTC, date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationMessage
from app.models.plan import Plan
from app.models.profile import Profile
from app.schemas.plan import PlanSummary
from app.services.ai_record_service import build_daily_summary

RECENT_MESSAGE_LIMIT = 10
RECENT_MESSAGE_CONTENT_LIMIT = 500
BOUNDED_CONTEXT_TEXT_LIMIT = 5000


def build_bounded_ai_context_data(
    db: Session,
    *,
    user_id: int,
    message: str,
    today: date,
) -> dict[str, Any]:
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
            .limit(RECENT_MESSAGE_LIMIT)
        )
    )
    return {
        "message": message,
        "today": today.isoformat(),
        "profile": _profile_summary(profile),
        "current_plan": _plan_summary(current_plan),
        "daily_summary": build_daily_summary(db, user_id=user_id, day=today).model_dump(mode="json"),
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
) -> str:
    return json.dumps(
        build_bounded_ai_context_data(db, user_id=user_id, message=message, today=today),
        ensure_ascii=False,
    )[:BOUNDED_CONTEXT_TEXT_LIMIT]


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
