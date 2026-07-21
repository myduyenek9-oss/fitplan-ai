from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from app.core.errors import PlanConflictError

from app.schemas.plan import MealPlan, PlanDayCreate, WorkoutPlan
from app.services.plan_service import PlanGenerator, PlanService


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


def _day_payload(day: date, calorie_target: float = 1800):
    return {
        "date": day.isoformat(),
        "calorie_target": calorie_target,
        "meals": [
            {
                "name": "Breakfast bowl",
                "meal_type": "breakfast",
                "calories": 500,
                "protein_g": 35,
                "carb_g": 50,
                "fat_g": 14,
            }
        ],
        "training_instruction": {
            "kind": "workout",
            "title": "Strength",
            "instructions": "Complete a controlled strength session",
            "duration_minutes": 45,
        },
    }


def _plan_payload(start: date, title="Manual plan"):
    return {"title": title, "days": [_day_payload(start + timedelta(days=i)) for i in range(7)]}


class FakePlanGenerator(PlanGenerator):
    def generate(self, *, start_date: date) -> list[PlanDayCreate]:
        return [
            PlanDayCreate(
                date=start_date + timedelta(days=offset),
                calorie_target=2000 + offset,
                meals=[
                    MealPlan(
                        name=f"Generated meal {offset + 1}",
                        meal_type="lunch",
                        calories=600,
                        protein_g=40,
                        carb_g=65,
                        fat_g=18,
                    )
                ],
                training_instruction=WorkoutPlan(
                    kind="rest" if offset == 6 else "workout",
                    title="Recovery" if offset == 6 else "Generated workout",
                    instructions="Rest and stretch" if offset == 6 else "Follow generated workout",
                    duration_minutes=None if offset == 6 else 30,
                ),
            )
            for offset in range(7)
        ]


def test_plan_endpoints_require_authentication(auth_client):
    assert auth_client.get("/api/plans/current").status_code == 401
    assert auth_client.post("/api/plans", json=_plan_payload(date(2026, 7, 20))).status_code == 401
    assert auth_client.post("/api/plans/generate", json={"start_date": "2026-07-20"}).status_code == 401


def test_create_current_get_and_activate_plan_versions(auth_client):
    headers = _auth_headers(auth_client)

    first_response = auth_client.post(
        "/api/plans",
        headers=headers,
        json=_plan_payload(date(2026, 7, 20), "First"),
    )
    second_response = auth_client.post(
        "/api/plans",
        headers=headers,
        json=_plan_payload(date(2026, 7, 27), "Second"),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.json()
    second = second_response.json()
    assert first["is_active"] is True
    assert second["is_active"] is True
    assert len(second["days"]) == 7
    assert [day["date"] for day in second["days"]] == [
        (date(2026, 7, 27) + timedelta(days=i)).isoformat() for i in range(7)
    ]

    current_response = auth_client.get("/api/plans/current", headers=headers)
    assert current_response.status_code == 200
    assert current_response.json()["id"] == second["id"]

    previous_response = auth_client.get(f"/api/plans/{first['id']}", headers=headers)
    assert previous_response.status_code == 200
    assert previous_response.json()["is_active"] is False
    assert len(previous_response.json()["days"]) == 7

    activate_response = auth_client.post(f"/api/plans/{first['id']}/activate", headers=headers)
    assert activate_response.status_code == 200
    assert activate_response.json()["id"] == first["id"]
    assert activate_response.json()["is_active"] is True
    assert auth_client.get(f"/api/plans/{second['id']}", headers=headers).json()["is_active"] is False


def test_generate_plan_uses_injected_generator_and_creates_active_seven_day_plan(auth_client):
    from app.api.plans import get_plan_generator
    from app.main import app

    headers = _auth_headers(auth_client)
    app.dependency_overrides[get_plan_generator] = lambda: FakePlanGenerator()

    response = auth_client.post(
        "/api/plans/generate",
        headers=headers,
        json={"start_date": "2026-07-20", "title": "Generated"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Generated"
    assert body["is_active"] is True
    assert len(body["days"]) == 7
    assert body["days"][0]["date"] == "2026-07-20"
    assert body["days"][0]["meals"][0]["name"] == "Generated meal 1"
    assert body["days"][6]["training_instruction"]["kind"] == "rest"


def test_plan_creation_rejects_missing_required_day_content_and_wrong_day_count(auth_client):
    headers = _auth_headers(auth_client)

    missing_meals = _plan_payload(date(2026, 7, 20))
    missing_meals["days"][0]["meals"] = []
    wrong_day_count = _plan_payload(date(2026, 7, 20))
    wrong_day_count["days"] = wrong_day_count["days"][:6]
    bad_calories = _plan_payload(date(2026, 7, 20))
    bad_calories["days"][0]["calorie_target"] = 0

    for payload in [missing_meals, wrong_day_count, bad_calories]:
        response = auth_client.post("/api/plans", headers=headers, json=payload)
        assert response.status_code == 422


def test_current_plan_returns_404_when_no_plan_exists(auth_client):
    headers = _auth_headers(auth_client)

    response = auth_client.get("/api/plans/current", headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize("field_path, value", [("calorie_target", "Infinity"), ("protein_g", "NaN")])
def test_plan_api_rejects_non_finite_float_values(auth_client, field_path, value):
    headers = _auth_headers(auth_client)
    payload = _plan_payload(date(2026, 7, 20))
    if field_path == "calorie_target":
        payload["days"][0][field_path] = value
    else:
        payload["days"][0]["meals"][0][field_path] = value

    response = auth_client.post("/api/plans", headers=headers, json=payload)

    assert response.status_code == 422


def test_plan_detail_and_activate_require_authentication(auth_client):
    assert auth_client.get("/api/plans/1").status_code == 401
    assert auth_client.post("/api/plans/1/activate").status_code == 401


def test_missing_plan_detail_and_activate_return_404(auth_client):
    headers = _auth_headers(auth_client)

    assert auth_client.get("/api/plans/999999", headers=headers).status_code == 404
    assert auth_client.post("/api/plans/999999/activate", headers=headers).status_code == 404


def test_damaged_plan_row_returns_controlled_500(monkeypatch, auth_client):
    headers = _auth_headers(auth_client)

    def load_damaged_plan(self, db, *, user_id, plan_id):
        return SimpleNamespace(
            id=plan_id,
            user_id=user_id,
            title="Damaged",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 26),
            is_active=True,
            days=[SimpleNamespace()],
            created_at=datetime(2026, 7, 20),
            updated_at=datetime(2026, 7, 20),
        )

    monkeypatch.setattr(PlanService, "get_plan", load_damaged_plan)
    response = auth_client.get("/api/plans/1", headers=headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "Plan data is invalid"


def test_repeated_activate_is_stable(auth_client):
    headers = _auth_headers(auth_client)
    created = auth_client.post(
        "/api/plans", headers=headers, json=_plan_payload(date(2026, 7, 20))
    )
    plan_id = created.json()["id"]

    first = auth_client.post(f"/api/plans/{plan_id}/activate", headers=headers)
    second = auth_client.post(f"/api/plans/{plan_id}/activate", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == plan_id
    assert second.json()["is_active"] is True


def test_plan_conflict_is_mapped_to_409(monkeypatch, auth_client):
    headers = _auth_headers(auth_client)

    def fail_create(*args, **kwargs):
        raise PlanConflictError

    monkeypatch.setattr(PlanService, "create_plan", fail_create)
    response = auth_client.post(
        "/api/plans", headers=headers, json=_plan_payload(date(2026, 7, 20))
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Plan conflict"


class InvalidPlanGenerator(PlanGenerator):
    def generate(self, *, start_date: date) -> list[PlanDayCreate]:
        return []


def test_invalid_generated_plan_returns_controlled_error_and_preserves_current_plan(auth_client):
    from app.api.plans import get_plan_generator
    from app.main import app

    headers = _auth_headers(auth_client)
    existing = auth_client.post(
        "/api/plans", headers=headers, json=_plan_payload(date(2026, 7, 20), "Existing")
    )
    existing_id = existing.json()["id"]
    app.dependency_overrides[get_plan_generator] = lambda: InvalidPlanGenerator()

    response = auth_client.post(
        "/api/plans/generate",
        headers=headers,
        json={"start_date": "2026-07-27", "title": "Invalid"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Plan data is invalid"
    current = auth_client.get("/api/plans/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == existing_id
    assert current.json()["is_active"] is True
