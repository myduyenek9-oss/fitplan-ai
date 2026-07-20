import pytest


PASSWORD = "correct horse battery staple"


def _auth_headers(client):
    client.post("/api/auth/setup", json={"username": "owner", "password": PASSWORD})
    token_response = client.post(
        "/api/auth/login",
        json={"username": "owner", "password": PASSWORD},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_profile_requires_authentication(auth_client):
    response = auth_client.get("/api/profile")

    assert response.status_code == 401


def test_authenticated_user_can_create_and_update_single_profile(auth_client):
    headers = _auth_headers(auth_client)

    create_response = auth_client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Owner",
            "sex": "female",
            "birth_date": "1990-05-01",
            "height_cm": 168.5,
            "timezone": "Asia/Shanghai",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["display_name"] == "Owner"
    assert created["sex"] == "female"
    assert created["height_cm"] == 168.5
    assert created["timezone"] == "Asia/Shanghai"

    update_response = auth_client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Updated Owner",
            "sex": "female",
            "birth_date": "1990-05-01",
            "height_cm": 169.0,
            "timezone": "UTC",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["display_name"] == "Updated Owner"
    assert updated["height_cm"] == 169.0

    get_response = auth_client.get("/api/profile", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["display_name"] == "Updated Owner"


def test_authenticated_user_can_save_and_update_active_goal(auth_client):
    headers = _auth_headers(auth_client)

    create_response = auth_client.put(
        "/api/profile/goal",
        headers=headers,
        json={
            "goal_type": "fat_loss",
            "daily_calories": 1800,
            "protein_g": 130,
            "carb_g": 180,
            "fat_g": 60,
            "activity_level": "moderate",
            "target_weight_kg": 62.5,
            "target_date": "2026-12-31",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["goal_type"] == "fat_loss"
    assert created["is_active"] is True
    assert created["daily_calories"] == 1800

    update_response = auth_client.put(
        "/api/profile/goal",
        headers=headers,
        json={
            "goal_type": "maintenance",
            "daily_calories": 2100,
            "protein_g": 120,
            "carb_g": 240,
            "fat_g": 70,
            "activity_level": "active",
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["goal_type"] == "maintenance"
    assert updated["daily_calories"] == 2100
    assert updated["target_weight_kg"] is None
    assert updated["is_active"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"weight_kg": -70, "logged_at": "2026-07-20T08:00:00Z"},
        {"weight_kg": 70, "body_fat_percent": 101, "logged_at": "2026-07-20T08:00:00Z"},
        {"weight_kg": 70, "waist_cm": -1, "logged_at": "2026-07-20T08:00:00Z"},
    ],
)
def test_body_metrics_reject_invalid_values(auth_client, payload):
    headers = _auth_headers(auth_client)

    response = auth_client.post("/api/body-metrics", headers=headers, json=payload)

    assert response.status_code == 422


def test_authenticated_user_can_save_and_list_body_metrics(auth_client):
    headers = _auth_headers(auth_client)

    first_response = auth_client.post(
        "/api/body-metrics",
        headers=headers,
        json={
            "weight_kg": 70.2,
            "body_fat_percent": 22.5,
            "waist_cm": 78.0,
            "chest_cm": 90.0,
            "hip_cm": 95.0,
            "logged_at": "2026-07-20T08:00:00Z",
        },
    )
    second_response = auth_client.post(
        "/api/body-metrics",
        headers=headers,
        json={"weight_kg": 69.8, "logged_at": "2026-07-21T08:00:00Z"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    list_response = auth_client.get("/api/body-metrics", headers=headers)
    assert list_response.status_code == 200
    metrics = list_response.json()
    assert [metric["weight_kg"] for metric in metrics] == [69.8, 70.2]
    assert metrics[1]["body_fat_percent"] == 22.5
    assert metrics[1]["waist_cm"] == 78.0
