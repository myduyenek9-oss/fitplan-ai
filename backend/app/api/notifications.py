from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.notification import DingTalkNotification
from app.models.profile import Profile
from app.models.user import User
from pydantic import BaseModel

from app.schemas.notification import (
    DingTalkNotificationResponse,
    DingTalkNotificationUpsert,
    DingTalkTestPushResponse,
)
from app.services.dingtalk import DingTalkError, DingTalkRobot, send_daily_push
from app.services.notification_secrets import (
    NotificationSecretError,
    decrypt_notification_secret,
    encrypt_notification_secret,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


class DingTalkNotificationStatusUpdate(BaseModel):
    is_enabled: bool



def _webhook_hint(webhook: str) -> str:
    token = webhook.rsplit("=", maxsplit=1)[-1]
    return "已绑定 · " + ("…" + token[-6:] if len(token) > 6 else "已隐藏")


def _response(notification: DingTalkNotification | None) -> DingTalkNotificationResponse:
    if notification is None:
        return DingTalkNotificationResponse(is_configured=False, is_enabled=False)
    try:
        webhook = decrypt_notification_secret(notification.webhook_encrypted)
    except NotificationSecretError:
        webhook = ""
    return DingTalkNotificationResponse(
        is_configured=bool(webhook),
        is_enabled=notification.is_enabled,
        webhook_hint=_webhook_hint(webhook) if webhook else "已保存（无法读取）",
        has_signing_secret=bool(notification.secret_encrypted),
        keyword=notification.keyword,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.get("/dingtalk", response_model=DingTalkNotificationResponse)
def get_dingtalk_notification(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DingTalkNotificationResponse:
    notification = db.scalar(
        select(DingTalkNotification).where(DingTalkNotification.user_id == current_user.id)
    )
    return _response(notification)


@router.put("/dingtalk", response_model=DingTalkNotificationResponse)
def upsert_dingtalk_notification(
    payload: DingTalkNotificationUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DingTalkNotificationResponse:
    try:
        webhook_encrypted = encrypt_notification_secret(payload.webhook)
        secret_encrypted = (
            encrypt_notification_secret(payload.secret) if payload.secret else None
        )
    except NotificationSecretError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    notification = db.scalar(
        select(DingTalkNotification).where(DingTalkNotification.user_id == current_user.id)
    )
    if notification is None:
        notification = DingTalkNotification(
            user_id=current_user.id,
            webhook_encrypted=webhook_encrypted,
            secret_encrypted=secret_encrypted,
            keyword=payload.keyword,
            is_enabled=payload.is_enabled,
        )
        db.add(notification)
    else:
        notification.webhook_encrypted = webhook_encrypted
        notification.secret_encrypted = secret_encrypted
        notification.keyword = payload.keyword
        notification.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(notification)
    return _response(notification)


@router.patch("/dingtalk/status", response_model=DingTalkNotificationResponse)
def set_dingtalk_notification_status(
    payload: DingTalkNotificationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DingTalkNotificationResponse:
    notification = db.scalar(
        select(DingTalkNotification).where(DingTalkNotification.user_id == current_user.id)
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DingTalk notification not found")
    notification.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(notification)
    return _response(notification)


@router.delete("/dingtalk", status_code=status.HTTP_204_NO_CONTENT)
def delete_dingtalk_notification(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    notification = db.scalar(
        select(DingTalkNotification).where(DingTalkNotification.user_id == current_user.id)
    )
    if notification is not None:
        db.delete(notification)
        db.commit()


@router.post("/dingtalk/test", response_model=DingTalkTestPushResponse)
def test_dingtalk_notification(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DingTalkTestPushResponse:
    notification = db.scalar(
        select(DingTalkNotification).where(DingTalkNotification.user_id == current_user.id)
    )
    if notification is None or not notification.is_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="DingTalk notification is not enabled")
    try:
        webhook = decrypt_notification_secret(notification.webhook_encrypted)
        secret = (
            decrypt_notification_secret(notification.secret_encrypted)
            if notification.secret_encrypted
            else ""
        )
        profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
        timezone = ZoneInfo(profile.timezone) if profile and profile.timezone else SHANGHAI_TIMEZONE
        send_daily_push(
            db,
            robot=DingTalkRobot(webhook=webhook, secret=secret),
            user_id=current_user.id,
            today=datetime.now(timezone).date(),
            keyword=notification.keyword,
        )
    except NotificationSecretError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except DingTalkError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DingTalkTestPushResponse()
