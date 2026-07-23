from datetime import date
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.services.dingtalk import (
    DingTalkError,
    DingTalkRobot,
    build_daily_push_markdown,
    send_daily_push,
    signed_webhook,
)
from app.services.notification_scheduler import create_daily_push_scheduler
from app.schemas.plan import MealPlan, PlanDay, WorkoutPlan


class FakeResponse:
    def __init__(self, payload: object, *, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> object:
        return self.payload


def test_signed_webhook_returns_original_url_without_secret():
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=test-token"

    assert signed_webhook(webhook, "", 1_700_000_000_000) == webhook


def test_signed_webhook_includes_timestamp_and_signature():
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=test-token"

    result = signed_webhook(webhook, "SECabc", 1_700_000_000_000)
    query = parse_qs(urlsplit(result).query)

    assert query["access_token"] == ["test-token"]
    assert query["timestamp"] == ["1700000000000"]
    assert len(query["sign"][0]) > 20


def test_robot_sends_markdown_payload(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: float):
        captured.update(url=url, json=json, timeout=timeout)
        return FakeResponse({"errcode": 0, "errmsg": "ok"})

    monkeypatch.setattr("app.services.dingtalk.httpx.post", fake_post)
    robot = DingTalkRobot(webhook="https://example.test/robot", secret="SECabc")

    robot.send_markdown(title="今日计划", text="完成训练", timestamp_ms=123)

    assert "timestamp=123" in str(captured["url"])
    assert captured["json"] == {
        "msgtype": "markdown",
        "markdown": {"title": "今日计划", "text": "完成训练"},
    }


def test_robot_raises_when_dingtalk_rejects_message(monkeypatch):
    monkeypatch.setattr(
        "app.services.dingtalk.httpx.post",
        lambda *args, **kwargs: FakeResponse({"errcode": 310000, "errmsg": "invalid sign"}),
    )

    with pytest.raises(DingTalkError, match="invalid sign"):
        DingTalkRobot(webhook="https://example.test/robot").send_markdown(title="t", text="body")



def test_daily_push_uses_scannable_markdown_tables(monkeypatch):
    today = date(2026, 7, 22)
    plan_day = PlanDay(
        date=today,
        calorie_target=2538,
        meals=[
            MealPlan(name="\u71d5\u9ea6|\u9e21\u86cb\u65e9\u9910", meal_type="breakfast", calories=634, protein_g=26, carb_g=92, fat_g=18),
            MealPlan(name="\u9e21\u80f8\u8089\u7c73\u996d\u5348\u9910", meal_type="lunch", calories=761, protein_g=32, carb_g=111, fat_g=21),
        ],
        training_instruction=WorkoutPlan(
            kind="rest",
            title="\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d",
            instructions="\u5b89\u6392\u6b65\u884c\u3001\u8f7b\u677e\u9a91\u8f66\u6216\u745c\u4f3d 20\u201330 \u5206\u949f\u3002",
            duration_minutes=25,
        ),
    )
    db = MagicMock()
    db.scalar.side_effect = [SimpleNamespace(display_name="inn"), SimpleNamespace(days=[plan_day])]
    monkeypatch.setattr(
        "app.services.dingtalk.build_daily_summary",
        lambda *_args, **_kwargs: SimpleNamespace(
            goal=SimpleNamespace(daily_calories=2538), remaining_calories=2538
        ),
    )

    title, content = build_daily_push_markdown(db, user_id=1, today=today)

    assert title == "FitPlan AI \u00b7 7/22 \u4eca\u65e5\u8ba1\u5212"
    assert content.startswith(
        "### \u65e9\u4e0a\u597d\uff0cinn \U0001f44b\u3000\u00b7\u3000\U0001f4c5 2026-07-22\n"
        "### \u4e0d\u6c42\u5b8c\u7f8e\uff0c\u5b8c\u6210\u4eca\u5929\u7684\u4e00\u5c0f\u6b65\u5c31\u5f88\u597d\u3002"
    )
    assert "| \u76ee\u6807\u70ed\u91cf | \u5f53\u524d\u53ef\u7528 |" in content
    assert "| \u9910\u6b21 | \u5177\u4f53\u5403\u4ec0\u4e48 | \u70ed\u91cf |" in content
    assert "| :---: | :---: | :---: |" in content
    assert "| \u65e9\u9910 | \u71d5\u9ea6\uff5c\u9e21\u86cb | **634 kcal** |" in content
    assert "| \u5348\u9910 | \u9e21\u80f8\u8089\u7c73\u996d | **761 kcal** |" in content
    assert "| \u9879\u76ee | \u5185\u5bb9 |" in content
    assert "| :---: | :---: |" in content
    assert "| \u8bad\u7ec3 | \u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d \u00b7 25 \u5206\u949f |" in content
    assert "| \u5b89\u6392 | \u5b89\u6392\u6b65\u884c\u3001\u8f7b\u677e\u9a91\u8f66\u6216\u745c\u4f3d 20\u201330 \u5206\u949f\u3002 |" in content


def test_daily_push_does_not_repeat_keyword_already_in_message(monkeypatch):
    robot = MagicMock()
    monkeypatch.setattr(
        "app.services.dingtalk.build_daily_push_markdown",
        lambda *_args, **_kwargs: ("今日计划", "### 今日热量\n\n原始内容"),
    )

    send_daily_push(
        MagicMock(),
        robot=robot,
        user_id=1,
        today=date(2026, 7, 22),
        keyword="热量",
    )

    robot.send_markdown.assert_called_once_with(
        title="今日计划",
        text="### 今日热量\n\n原始内容",
    )


def test_daily_push_adds_missing_keyword_as_subtle_footer(monkeypatch):
    robot = MagicMock()
    monkeypatch.setattr(
        "app.services.dingtalk.build_daily_push_markdown",
        lambda *_args, **_kwargs: ("今日计划", "### 原始内容"),
    )

    send_daily_push(
        MagicMock(),
        robot=robot,
        user_id=1,
        today=date(2026, 7, 22),
        keyword="热量计划",
    )

    robot.send_markdown.assert_called_once_with(
        title="今日计划",
        text="### 原始内容\n\n_FitPlan AI · 热量计划_",
    )


def test_scheduler_runs_without_legacy_webhook_for_database_backed_notifications():
    scheduler = create_daily_push_scheduler(Settings(dingtalk_webhook=""))
    assert scheduler is not None
    assert scheduler.get_job("fitplan-daily-dingtalk-push") is not None


def test_scheduler_uses_configured_daily_time():
    scheduler = create_daily_push_scheduler(
        Settings(
            dingtalk_webhook="https://example.test/robot",
            dingtalk_daily_push_hour=7,
            dingtalk_daily_push_minute=30,
        )
    )
    assert scheduler is not None
    job = scheduler.get_job("fitplan-daily-dingtalk-push")
    assert job is not None
    assert str(job.trigger) == "cron[hour='7', minute='30']"
