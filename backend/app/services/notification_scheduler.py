from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import Settings
from app.db.session import SessionLocal, get_engine
from app.services.dingtalk import DingTalkRobot, configured_user_ids, send_daily_push


logger = logging.getLogger(__name__)
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


def run_daily_push(settings: Settings) -> None:
    """Deliver each saved user's daily plan without letting one failure stop the job."""
    if not settings.dingtalk_webhook:
        return

    robot = DingTalkRobot(webhook=settings.dingtalk_webhook, secret=settings.dingtalk_secret)
    db = SessionLocal(bind=get_engine())
    try:
        today = datetime.now(SHANGHAI_TIMEZONE).date()
        for user_id in configured_user_ids(db):
            try:
                send_daily_push(db, robot=robot, user_id=user_id, today=today)
            except Exception:
                logger.exception("Unable to send daily DingTalk plan for user_id=%s", user_id)
    finally:
        db.close()


def create_daily_push_scheduler(settings: Settings) -> BackgroundScheduler | None:
    """Create the optional Shanghai-time daily push scheduler."""
    if not settings.dingtalk_webhook:
        return None

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
