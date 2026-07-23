from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.config import Settings
from app.db.session import SessionLocal, get_engine
from app.models.notification import DingTalkNotification
from app.models.profile import Profile
from app.models.user import User
from app.services.dingtalk import DingTalkRobot, enabled_dingtalk_notifications, send_daily_push
from app.services.notification_secrets import NotificationSecretError, decrypt_notification_secret


logger = logging.getLogger(__name__)
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _user_timezone(db, user_id: int) -> ZoneInfo:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if not profile or not profile.timezone:
        return SHANGHAI_TIMEZONE
    try:
        return ZoneInfo(profile.timezone)
    except Exception:
        return SHANGHAI_TIMEZONE


def _send_with_saved_notification(db, notification: DingTalkNotification) -> None:
    webhook = decrypt_notification_secret(notification.webhook_encrypted)
    secret = (
        decrypt_notification_secret(notification.secret_encrypted)
        if notification.secret_encrypted
        else ""
    )
    today = datetime.now(_user_timezone(db, notification.user_id)).date()
    send_daily_push(
        db,
        robot=DingTalkRobot(webhook=webhook, secret=secret),
        user_id=notification.user_id,
        today=today,
        keyword=notification.keyword,
    )


def run_daily_push(settings: Settings) -> None:
    """Send each account only to its own saved DingTalk robot.

    The former environment-level robot remains as a migration fallback only for
    users that have never opened notification settings. Once a user saves or
    disables their own setting, the shared fallback no longer receives their plan.
    """
    db = SessionLocal(bind=get_engine())
    try:
        saved_notifications = list(
            db.scalars(select(DingTalkNotification).order_by(DingTalkNotification.user_id))
        )
        saved_user_ids = {notification.user_id for notification in saved_notifications}
        for notification in enabled_dingtalk_notifications(db):
            try:
                _send_with_saved_notification(db, notification)
            except NotificationSecretError:
                logger.exception("Unable to decrypt DingTalk notification for user_id=%s", notification.user_id)
            except Exception:
                logger.exception("Unable to send daily DingTalk plan for user_id=%s", notification.user_id)

        if not settings.dingtalk_webhook:
            return

        # Compatibility for deployments created before per-account settings.
        legacy_robot = DingTalkRobot(webhook=settings.dingtalk_webhook, secret=settings.dingtalk_secret)
        for user_id in db.scalars(select(User.id).order_by(User.id)):
            if user_id in saved_user_ids:
                continue
            try:
                today = datetime.now(_user_timezone(db, user_id)).date()
                send_daily_push(db, robot=legacy_robot, user_id=user_id, today=today)
            except Exception:
                logger.exception("Unable to send legacy DingTalk plan for user_id=%s", user_id)
    finally:
        db.close()


def create_daily_push_scheduler(settings: Settings) -> BackgroundScheduler:
    """Run daily so database-backed user notification settings can work."""
    scheduler = BackgroundScheduler(timezone=SHANGHAI_TIMEZONE)
    scheduler.add_job(
        run_daily_push,
        trigger="cron",
        args=[settings],
        hour=settings.dingtalk_daily_push_hour,
        minute=settings.dingtalk_daily_push_minute,
        id="fitplan-daily-dingtalk-push",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler
