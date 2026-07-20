import pytest
from fastapi.testclient import TestClient


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


def _save_goal(client, headers):
    response = client.put(
        "/api/profile/goal",
        headers=headers,
        json={
            "goal_type": "fat_loss",
            "daily_calories": 2000,
            "protein_g": 150,
            "carb_g": 200,
            "fat_g": 70,
            "activity_level": "moderate",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_record_endpoints_require_authentication(auth_client):
    assert auth_client.post("/api/records/food", json={}).status_code == 401
    assert auth_client.post("/api/records/exercise", json={}).status_code == 401
    assert auth_client.get("/api/records/daily?date=2026-07-20").status_code == 401


def test_create_food_and_exercise_logs_and_daily_summary(auth_client):
    headers = _auth_headers(auth_client)
    _save_goal(auth_client, headers)

    food_response = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "早餐 鸡蛋两个 牛奶一杯",
            "parsed_content": {"items": [{"name": "eggs", "quantity": "2"}]},
            "meal_type": "breakfast",
            "calories": 500,
            "protein_g": 35,
            "carb_g": 40,
            "fat_g": 20,
            "logged_at": "2026-07-20T08:30:00Z",
        },
    )
    exercise_response = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "running",
            "description": "5km easy run",
            "duration_minutes": 35,
            "calories_burned": 300,
            "logged_at": "2026-07-20T10:00:00Z",
        },
    )

    assert food_response.status_code == 201
    food = food_response.json()
    assert food["status"] == "active"
    assert food["parsed_content"] == {"items": [{"name": "eggs", "quantity": "2"}]}
    assert exercise_response.status_code == 201

    summary_response = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["date"] == "2026-07-20"
    assert summary["food_totals"] == {
        "calories": 500.0,
        "protein_g": 35.0,
        "carb_g": 40.0,
        "fat_g": 20.0,
    }
    assert summary["exercise_totals"] == {"calories_burned": 300.0, "duration_minutes": 35.0}
    assert summary["remaining_calories"] == 1800.0
    assert summary["macro_completion_percentages"] == {
        "protein_g": 23.33,
        "carb_g": 20.0,
        "fat_g": 28.57,
    }


def test_records_reject_negative_quantities(auth_client):
    headers = _auth_headers(auth_client)

    negative_food = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "bad",
            "calories": -1,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "logged_at": "2026-07-20T08:30:00Z",
        },
    )
    negative_exercise = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "running",
            "duration_minutes": -5,
            "calories_burned": 100,
            "logged_at": "2026-07-20T10:00:00Z",
        },
    )

    assert negative_food.status_code == 422
    assert negative_exercise.status_code == 422


def test_patch_delete_and_undo_food_records_are_reflected_in_daily_summary(auth_client):
    headers = _auth_headers(auth_client)
    _save_goal(auth_client, headers)

    first = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "lunch",
            "calories": 400,
            "protein_g": 20,
            "carb_g": 50,
            "fat_g": 10,
            "logged_at": "2026-07-20T12:00:00Z",
        },
    ).json()
    second = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "snack",
            "calories": 200,
            "protein_g": 5,
            "carb_g": 30,
            "fat_g": 8,
            "logged_at": "2026-07-20T15:00:00Z",
        },
    ).json()
    third = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "mistake",
            "calories": 300,
            "protein_g": 10,
            "carb_g": 45,
            "fat_g": 12,
            "logged_at": "2026-07-20T18:00:00Z",
        },
    ).json()

    patch_response = auth_client.patch(
        f"/api/records/food/{first['id']}",
        headers=headers,
        json={"calories": 450, "protein_g": 25, "parsed_content": {"corrected": True}},
    )
    delete_response = auth_client.delete(f"/api/records/food/{second['id']}", headers=headers)
    undo_response = auth_client.post(f"/api/records/food/{third['id']}/undo", headers=headers)

    assert patch_response.status_code == 200
    assert patch_response.json()["calories"] == 450.0
    assert patch_response.json()["parsed_content"] == {"corrected": True}
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    assert undo_response.status_code == 200
    assert undo_response.json()["status"] == "undone"

    summary_response = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["food_totals"] == {
        "calories": 450.0,
        "protein_g": 25.0,
        "carb_g": 50.0,
        "fat_g": 10.0,
    }
    assert summary["food_status_counts"] == {"active": 1, "deleted": 1, "undone": 1}
    assert summary["remaining_calories"] == 1550.0


def test_daily_summary_without_goal_uses_null_goal_and_remaining_calories(auth_client):
    headers = _auth_headers(auth_client)

    auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "breakfast",
            "calories": 250,
            "protein_g": 15,
            "carb_g": 30,
            "fat_g": 7,
            "logged_at": "2026-07-20T08:00:00Z",
        },
    )

    summary_response = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["goal"] is None
    assert summary["remaining_calories"] is None
    assert summary["macro_completion_percentages"] == {
        "protein_g": None,
        "carb_g": None,
        "fat_g": None,
    }


def _save_profile_timezone(client, headers, timezone="Asia/Shanghai"):
    response = client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Owner",
            "sex": "female",
            "birth_date": "1990-05-01",
            "height_cm": 168,
            "timezone": timezone,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_daily_summary_uses_profile_timezone_local_date_bounds(auth_client):
    headers = _auth_headers(auth_client)
    _save_profile_timezone(auth_client, headers, "Asia/Shanghai")
    _save_goal(auth_client, headers)

    food_response = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "midnight snack",
            "calories": 120,
            "protein_g": 10,
            "carb_g": 12,
            "fat_g": 4,
            "logged_at": "2026-07-20T00:30:00+08:00",
        },
    )
    exercise_response = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "walking",
            "duration_minutes": 30,
            "calories_burned": 80,
            "logged_at": "2026-07-20T00:45:00+08:00",
        },
    )

    assert food_response.status_code == 201
    assert food_response.json()["logged_at"].endswith("+08:00")
    assert exercise_response.status_code == 201
    assert exercise_response.json()["logged_at"].endswith("+08:00")

    local_day = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)
    previous_local_day = auth_client.get("/api/records/daily?date=2026-07-19", headers=headers)

    assert local_day.status_code == 200
    assert local_day.json()["food_totals"]["calories"] == 120.0
    assert local_day.json()["exercise_totals"] == {"calories_burned": 80.0, "duration_minutes": 30.0}
    assert previous_local_day.status_code == 200
    assert previous_local_day.json()["food_totals"]["calories"] == 0.0
    assert previous_local_day.json()["exercise_totals"] == {"calories_burned": 0.0, "duration_minutes": 0.0}


def test_record_logged_at_requires_timezone_offset(auth_client):
    headers = _auth_headers(auth_client)

    food_response = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "naive time",
            "calories": 100,
            "protein_g": 10,
            "carb_g": 10,
            "fat_g": 2,
            "logged_at": "2026-07-20T08:30:00",
        },
    )
    exercise_response = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "running",
            "duration_minutes": 30,
            "calories_burned": 200,
            "logged_at": "2026-07-20T10:00:00",
        },
    )

    assert food_response.status_code == 422
    assert exercise_response.status_code == 422


@pytest.mark.parametrize("field", ["original_text", "calories", "parsed_content", "logged_at"])
def test_patch_food_rejects_null_for_non_nullable_fields(auth_client, field):
    headers = _auth_headers(auth_client)
    record = auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "lunch",
            "calories": 400,
            "protein_g": 20,
            "carb_g": 50,
            "fat_g": 10,
            "logged_at": "2026-07-20T12:00:00Z",
        },
    ).json()
    no_raise_client = TestClient(auth_client.app, raise_server_exceptions=False)

    response = no_raise_client.patch(
        f"/api/records/food/{record['id']}", headers=headers, json={field: None}
    )

    assert response.status_code == 422


def test_exercise_rejects_zero_duration_and_calories(auth_client):
    headers = _auth_headers(auth_client)

    zero_duration = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "running",
            "duration_minutes": 0,
            "calories_burned": 100,
            "logged_at": "2026-07-20T10:00:00Z",
        },
    )
    zero_calories = auth_client.post(
        "/api/records/exercise",
        headers=headers,
        json={
            "exercise_type": "running",
            "duration_minutes": 30,
            "calories_burned": 0,
            "logged_at": "2026-07-20T10:00:00Z",
        },
    )

    assert zero_duration.status_code == 422
    assert zero_calories.status_code == 422


def test_daily_summary_uses_latest_active_goal_after_repeated_updates(auth_client):
    headers = _auth_headers(auth_client)
    _save_goal(auth_client, headers)
    latest_goal = auth_client.put(
        "/api/profile/goal",
        headers=headers,
        json={
            "goal_type": "maintenance",
            "daily_calories": 2500,
            "protein_g": 160,
            "carb_g": 300,
            "fat_g": 80,
            "activity_level": "active",
        },
    )
    auth_client.post(
        "/api/records/food",
        headers=headers,
        json={
            "original_text": "breakfast",
            "calories": 500,
            "protein_g": 20,
            "carb_g": 60,
            "fat_g": 12,
            "logged_at": "2026-07-20T08:00:00Z",
        },
    )

    summary_response = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)

    assert latest_goal.status_code == 200
    assert latest_goal.json()["daily_calories"] == 2500
    assert summary_response.status_code == 200
    assert summary_response.json()["goal"]["daily_calories"] == 2500.0
    assert summary_response.json()["remaining_calories"] == 2000.0
