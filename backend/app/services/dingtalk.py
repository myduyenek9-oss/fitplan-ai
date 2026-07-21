from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote_plus, urlencode, urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.plan import Plan
from app.models.profile import Profile
from app.models.user import User
from app.schemas.plan import PlanDay as PlanDaySchema
from app.services.ai_record_service import build_daily_summary


class DingTalkError(RuntimeError):
    """Raised when a DingTalk robot request cannot be delivered."""


def signed_webhook(webhook: str, secret: str, timestamp_ms: int) -> str:
    """Append DingTalk's optional timestamp and HMAC-SHA256 signature to a webhook."""
    if not secret:
        return webhook

    string_to_sign = f"{timestamp_ms}\\n{secret}".encode("utf-8")
    signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    ).decode("utf-8")
    parts = urlsplit(webhook)
    signature_query = urlencode(
        {"timestamp": str(timestamp_ms), "sign": signature},
        quote_via=quote_plus,
    )
    query = "&".join(part for part in (parts.query, signature_query) if part)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


@dataclass(frozen=True)
class DingTalkRobot:
    webhook: str
    secret: str = ""
    timeout_seconds: float = 10.0

    def send_markdown(self, *, title: str, text: str, timestamp_ms: int | None = None) -> None:
        """Send a markdown message through a DingTalk custom robot webhook."""
        if not self.webhook:
            raise DingTalkError("DingTalk webhook is not configured")
        if timestamp_ms is None:
            from time import time

            timestamp_ms = int(time() * 1000)

        try:
            response = httpx.post(
                signed_webhook(self.webhook, self.secret, timestamp_ms),
                json={"msgtype": "markdown", "markdown": {"title": title, "text": text}},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise DingTalkError(f"DingTalk webhook request failed: {exc}") from exc
        except ValueError as exc:
            raise DingTalkError("DingTalk webhook returned invalid JSON") from exc

        if not isinstance(payload, dict) or payload.get("errcode") != 0:
            detail = payload.get("errmsg") if isinstance(payload, dict) else "invalid response"
            raise DingTalkError(f"DingTalk webhook rejected the message: {detail}")


def _current_day(plan: Plan | None, today: date) -> PlanDaySchema | None:
    if plan is None:
        return None
    for plan_day in plan.days:
        if plan_day.date == today:
            return PlanDaySchema(
                date=plan_day.date,
                calorie_target=plan_day.calorie_target,
                meals=plan_day.meals,
                training_instruction=plan_day.training_instruction,
            )
    return None


def build_daily_push_markdown(db: Session, *, user_id: int, today: date) -> tuple[str, str]:
    """Build a concise, actionable daily plan message for a DingTalk robot."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    summary = build_daily_summary(db, user_id=user_id, day=today)
    plan = db.scalar(
        select(Plan)
        .options(selectinload(Plan.days))
        .where(Plan.user_id == user_id, Plan.is_active.is_(True))
        .order_by(Plan.updated_at.desc(), Plan.id.desc())
        .limit(1)
    )
    plan_day = _current_day(plan, today)
    name = profile.display_name if profile and profile.display_name else "训练伙伴"

    lines = [
        f"### 早上好，{name} 👋",
        f"> {today.isoformat()} · 不求完美，完成今天的一小步就很好。",
        "",
    ]
    if summary.goal is not None:
        lines.extend(
            [
                "#### 今日热量",
                f"- 目标：**{int(summary.goal.daily_calories)} kcal**",
                f"- 当前可用：**{int(summary.remaining_calories or 0)} kcal**",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "#### 先完成基础目标设置",
                "- 打开 FitPlan AI 填写体重、活动水平和健身方向，AI 才能计算今日热量。",
                "",
            ]
        )

    if plan_day is not None:
        lines.append("#### 今日饮食安排")
        for meal in plan_day.meals:
            lines.append(f"- {meal.name}（约 {int(meal.calories)} kcal）")
        lines.extend(
            [
                "",
                "#### 今日训练",
                f"- **{plan_day.training_instruction.title}**：{plan_day.training_instruction.instructions}",
            ]
        )
    else:
        lines.extend(
            [
                "#### 今日行动",
                "- 记录第一餐或一次运动；有临时变化，直接告诉 AI 来调整计划。",
            ]
        )

    lines.extend(
        [
            "",
            "_吃了什么、完成了什么运动，都可以在 FitPlan AI 里用自然语言补记。_",
        ]
    )
    return "FitPlan AI · 今日计划", "\\n".join(lines)


def send_daily_push(db: Session, *, robot: DingTalkRobot, user_id: int, today: date) -> None:
    title, content = build_daily_push_markdown(db, user_id=user_id, today=today)
    robot.send_markdown(title=title, text=content)


def configured_user_ids(db: Session) -> list[int]:
    """Return user ids explicitly stored in the application database."""
    return list(db.scalars(select(User.id).order_by(User.id)))
