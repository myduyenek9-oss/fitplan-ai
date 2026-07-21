from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.ai import get_ai_client
from app.api.deps import get_current_user, get_db
from app.models.conversation import ConversationMessage
from app.models.user import User
from app.schemas.chat import ChatHistoryMessage, ChatRequest, ChatResponse
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_context import build_bounded_ai_context_text
from app.services.ai_prompts import CHAT_SYSTEM_PROMPT

router = APIRouter(prefix="/api/ai", tags=["ai"])


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
    return [ChatHistoryMessage.model_validate(message) for message in reversed(messages)]


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
            user=build_bounded_ai_context_text(db, user_id=current_user.id, message=payload.message, today=today),
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
