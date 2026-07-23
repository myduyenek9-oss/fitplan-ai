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

from app.models.notification import DingTalkNotification
from app.models.plan import Plan
from app.models.profile import Profile
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


def _table_cell(value: object) -> str:
    """Keep dynamic values inside one DingTalk Markdown table cell."""
    return str(value).replace("|", "\uff5c").replace("\r", " ").replace("\n", " ").strip()


def _meal_label(meal_type: str | None) -> str:
    return {
        "breakfast": "\u65e9\u9910",
        "lunch": "\u5348\u9910",
        "snack": "\u52a0\u9910",
        "dinner": "\u665a\u9910",
    }.get(meal_type or "", "\u996e\u98df")


def _meal_name(meal_name: object, meal_type: str | None) -> str:
    """Avoid repeating the meal label in the food column, keeping short names on one line."""
    value = _table_cell(meal_name)
    label = _meal_label(meal_type)
    if label != "\u996e\u98df" and value.endswith(label) and len(value) > len(label):
        return value[: -len(label)].rstrip()
    return value


def build_daily_push_markdown(db: Session, *, user_id: int, today: date) -> tuple[str, str]:
    """Build a scannable, table-style daily plan for a DingTalk robot."""
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
    name = _table_cell(profile.display_name) if profile and profile.display_name else "\u8bad\u7ec3\u4f19\u4f34"

    lines = [
        f"### \u65e9\u4e0a\u597d\uff0c{name} \U0001f44b\u3000\u00b7\u3000\U0001f4c5 {today.isoformat()}",
        "### \u4e0d\u6c42\u5b8c\u7f8e\uff0c\u5b8c\u6210\u4eca\u5929\u7684\u4e00\u5c0f\u6b65\u5c31\u5f88\u597d\u3002",
        "",
        "---",
        "",
    ]
    if summary.goal is not None:
        lines.extend(
            [
                "**\U0001f4ca \u4eca\u65e5\u70ed\u91cf**",
                "",
                "| \u76ee\u6807\u70ed\u91cf | \u5f53\u524d\u53ef\u7528 |",
                "| :---: | :---: |",
                f"| **{int(summary.goal.daily_calories)} kcal** | **{int(summary.remaining_calories or 0)} kcal** |",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "**\U0001f4ca \u4eca\u65e5\u76ee\u6807**",
                "",
                "| \u4e0b\u4e00\u6b65 |",
                "| :--- |",
                "| \u6253\u5f00 FitPlan AI \u586b\u5199\u4f53\u91cd\u3001\u6d3b\u52a8\u6c34\u5e73\u548c\u5065\u8eab\u65b9\u5411\uff0cAI \u624d\u80fd\u8ba1\u7b97\u4eca\u65e5\u70ed\u91cf\u3002 |",
                "",
            ]
        )

    if plan_day is not None:
        lines.extend(
            [
                "**\U0001f37d\ufe0f \u4eca\u65e5\u996e\u98df\u5b89\u6392**",
                "",
                "| \u9910\u6b21 | \u5177\u4f53\u5403\u4ec0\u4e48 | \u70ed\u91cf |",
                "| :---: | :---: | :---: |",
            ]
        )
        for meal in plan_day.meals:
            lines.append(
                f"| {_meal_label(meal.meal_type)} | {_meal_name(meal.name, meal.meal_type)} | **{int(meal.calories)} kcal** |"
            )
        training = plan_day.training_instruction
        duration = f" \u00b7 {int(training.duration_minutes)} \u5206\u949f" if training.duration_minutes else ""
        lines.extend(
            [
                "",
                "**\U0001f3cb\ufe0f \u4eca\u65e5\u8bad\u7ec3**",
                "",
                "| \u9879\u76ee | \u5185\u5bb9 |",
                "| :---: | :---: |",
                f"| \u8bad\u7ec3 | {_table_cell(training.title)}{duration} |",
                f"| \u5b89\u6392 | {_table_cell(training.instructions)} |",
            ]
        )
    else:
        lines.extend(
            [
                "**\u2705 \u4eca\u65e5\u884c\u52a8**",
                "",
                "| \u5efa\u8bae |",
                "| :--- |",
                "| \u8bb0\u5f55\u7b2c\u4e00\u9910\u6216\u4e00\u6b21\u8fd0\u52a8\uff1b\u6709\u4e34\u65f6\u53d8\u5316\uff0c\u76f4\u63a5\u544a\u8bc9 AI \u6765\u8c03\u6574\u8ba1\u5212\u3002 |",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "_\U0001f4ac \u5403\u4e86\u4ec0\u4e48\u3001\u5b8c\u6210\u4e86\u4ec0\u4e48\u8fd0\u52a8\uff0c\u90fd\u53ef\u4ee5\u5728 FitPlan AI \u91cc\u7528\u81ea\u7136\u8bed\u8a00\u8865\u8bb0\u3002_",
        ]
    )
    return f"FitPlan AI \u00b7 {today.month}/{today.day} \u4eca\u65e5\u8ba1\u5212", "\n".join(lines)

def send_daily_push(
    db: Session,
    *,
    robot: DingTalkRobot,
    user_id: int,
    today: date,
    keyword: str | None = None,
) -> None:
    title, content = build_daily_push_markdown(db, user_id=user_id, today=today)
    normalized_keyword = keyword.replace("\r", " ").replace("\n", " ").strip() if keyword else ""
    if normalized_keyword and normalized_keyword not in content:
        content = f"{content}\n\n_FitPlan AI · {normalized_keyword}_"
    robot.send_markdown(title=title, text=content)


def enabled_dingtalk_notifications(db: Session) -> list[DingTalkNotification]:
    """Return each user's enabled notification configuration, never a shared robot."""
    return list(
        db.scalars(
            select(DingTalkNotification)
            .where(DingTalkNotification.is_enabled.is_(True))
            .order_by(DingTalkNotification.user_id)
        )
    )
