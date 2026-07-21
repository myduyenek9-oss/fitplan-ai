from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import Settings
from app.services.dingtalk import DingTalkError, DingTalkRobot, signed_webhook
from app.services.notification_scheduler import create_daily_push_scheduler


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


def test_scheduler_is_disabled_without_webhook():
    assert create_daily_push_scheduler(Settings(dingtalk_webhook="")) is None


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
