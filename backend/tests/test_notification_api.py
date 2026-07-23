
PASSWORD = "correct horse battery staple"
WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=very-private-token"


def _headers(client):
    client.post("/api/auth/setup", json={"username": "notify-owner", "password": PASSWORD})
    login = client.post("/api/auth/login", json={"username": "notify-owner", "password": PASSWORD})
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def test_user_can_save_read_toggle_and_delete_own_dingtalk_notification(auth_client):
    headers = _headers(auth_client)

    initial = auth_client.get("/api/notifications/dingtalk", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["is_configured"] is False

    saved = auth_client.put(
        "/api/notifications/dingtalk",
        headers=headers,
        json={"webhook": WEBHOOK, "secret": "SEC-private-sign", "keyword": "热量计划", "is_enabled": True},
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["is_configured"] is True
    assert body["is_enabled"] is True
    assert body["has_signing_secret"] is True
    assert body["keyword"] == "热量计划"
    assert "very-private-token" not in saved.text
    assert "SEC-private-sign" not in saved.text

    fetched = auth_client.get("/api/notifications/dingtalk", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["webhook_hint"].endswith("-token")
    assert fetched.json()["keyword"] == "热量计划"

    paused = auth_client.patch(
        "/api/notifications/dingtalk/status", headers=headers, json={"is_enabled": False}
    )
    assert paused.status_code == 200
    assert paused.json()["is_enabled"] is False

    deleted = auth_client.delete("/api/notifications/dingtalk", headers=headers)
    assert deleted.status_code == 204
    assert auth_client.get("/api/notifications/dingtalk", headers=headers).json()["is_configured"] is False


def test_dingtalk_notification_requires_https_webhook(auth_client):
    headers = _headers(auth_client)
    response = auth_client.put(
        "/api/notifications/dingtalk",
        headers=headers,
        json={"webhook": "http://example.test/robot", "is_enabled": True},
    )
    assert response.status_code == 422


def test_user_can_send_test_push_only_to_their_saved_robot(auth_client, monkeypatch):
    headers = _headers(auth_client)
    auth_client.put(
        "/api/notifications/dingtalk",
        headers=headers,
        json={"webhook": WEBHOOK, "secret": "SEC-private-sign", "keyword": "热量计划", "is_enabled": True},
    )
    captured: dict[str, object] = {}

    def fake_send(db, *, robot, user_id, today, keyword=None):
        captured.update(
            webhook=robot.webhook,
            secret=robot.secret,
            user_id=user_id,
            today=today,
            keyword=keyword,
        )

    monkeypatch.setattr("app.api.notifications.send_daily_push", fake_send)
    response = auth_client.post("/api/notifications/dingtalk/test", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"delivered": True}
    assert captured["webhook"] == WEBHOOK
    assert captured["secret"] == "SEC-private-sign"
    assert captured["user_id"] == 1
    assert captured["keyword"] == "热量计划"
