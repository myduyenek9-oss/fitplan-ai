
from fastapi.testclient import TestClient

from app.services.ai_client import AiProviderError
from tests.fakes import FakeAiClient


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


def _food_result():
    return {
        "meal_type": "snack",
        "logged_at": "2026-07-20T14:30:00+08:00",
        "confidence": 0.82,
        "items": [
            {"name": "鸡腿堡", "quantity": "1个", "calories": 520, "protein_g": 24, "carb_g": 50, "fat_g": 25},
            {"name": "奶茶", "quantity": "1杯", "calories": 360, "protein_g": 5, "carb_g": 58, "fat_g": 11},
        ],
        "adjustment_suggestion": "晚餐减少油脂和精制碳水。",
    }


def test_ai_record_endpoints_require_authentication(auth_client):
    assert auth_client.post("/api/records/food/natural-language", json={"text": "加餐"}).status_code == 401
    assert auth_client.post("/api/records/exercise/natural-language", json={"text": "跑步"}).status_code == 401
    assert auth_client.post("/api/ai/chat", json={"message": "怎么调整"}).status_code == 401



def test_natural_language_and_chat_endpoints_reject_blank_text(auth_client):
    headers = _auth_headers(auth_client)

    assert auth_client.post(
        "/api/records/food/natural-language",
        headers=headers,
        json={"text": "   ", "today": "2026-07-20"},
    ).status_code == 422
    assert auth_client.post(
        "/api/records/exercise/natural-language",
        headers=headers,
        json={"text": "   ", "today": "2026-07-20"},
    ).status_code == 422
    assert auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "   ", "today": "2026-07-20"},
    ).status_code == 422


def test_food_natural_language_endpoint_creates_record_and_returns_summary(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    fake = FakeAiClient(json_responses=[_food_result()])
    app.dependency_overrides[get_ai_client] = lambda: fake

    response = auth_client.post(
        "/api/records/food/natural-language",
        headers=headers,
        json={"text": "刚才吃了一个鸡腿堡和一杯奶茶", "today": "2026-07-20"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["record"]["original_text"] == "刚才吃了一个鸡腿堡和一杯奶茶"
    assert body["record"]["calories"] == 880
    assert [item["name"] for item in body["record"]["parsed_content"]["items"]] == ["鸡腿堡", "奶茶"]
    assert body["daily_summary"]["food_totals"]["calories"] == 880
    assert body["adjustment_suggestion"] == "晚餐减少油脂和精制碳水。"
    assert "JSON only" in fake.json_calls[0]["system"]
    assert "诊断" in fake.json_calls[0]["system"]


def test_food_natural_language_provider_error_returns_readable_error_without_record(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClient(
        json_error=AiProviderError("AI provider timed out")
    )
    no_raise_client = TestClient(auth_client.app, raise_server_exceptions=False)

    response = no_raise_client.post(
        "/api/records/food/natural-language",
        headers=headers,
        json={"text": "加餐薯片一包", "today": "2026-07-20"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider timed out"
    summary = auth_client.get("/api/records/daily?date=2026-07-20", headers=headers)
    assert summary.json()["food_totals"]["calories"] == 0


def test_exercise_natural_language_endpoint_creates_record(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClient(
        json_responses=[
            {
                "exercise_type": "running",
                "description": "慢跑 30 分钟",
                "duration_minutes": 30,
                "calories_burned": 240,
                "logged_at": "2026-07-20T19:30:00+08:00",
                "confidence": 0.9,
                "adjustment_suggestion": "今天已有有氧运动，睡前注意拉伸。",
            }
        ]
    )

    response = auth_client.post(
        "/api/records/exercise/natural-language",
        headers=headers,
        json={"text": "晚上慢跑了30分钟", "today": "2026-07-20"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["record"]["exercise_type"] == "running"
    assert body["daily_summary"]["exercise_totals"]["calories_burned"] == 240


def test_ai_chat_uses_bounded_context_and_saves_conversation(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    fake = FakeAiClient(text_responses=["今天晚餐建议选择高蛋白、低油的食物。"])
    app.dependency_overrides[get_ai_client] = lambda: fake

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "我今天多吃了，晚餐怎么调整？", "today": "2026-07-20"},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "今天晚餐建议选择高蛋白、低油的食物。"
    assert "AI_API_KEY" not in fake.text_calls[0]["user"]
    assert "password_hash" not in fake.text_calls[0]["user"]
    assert len(fake.text_calls[0]["user"]) < 5000



class RecordingPlanGenerator:
    def __init__(self):
        self.context = None

    def generate(self, *, start_date, context=None):
        from app.schemas.plan import MealPlan, PlanDayCreate, WorkoutPlan
        from datetime import timedelta

        self.context = context
        return [
            PlanDayCreate(
                date=start_date + timedelta(days=offset),
                calorie_target=1900 + offset,
                meals=[
                    MealPlan(
                        name=f"Context meal {offset + 1}",
                        meal_type="lunch",
                        calories=600,
                        protein_g=35,
                        carb_g=65,
                        fat_g=18,
                    )
                ],
                training_instruction=WorkoutPlan(
                    kind="rest" if offset == 6 else "workout",
                    title="Recovery" if offset == 6 else "Context workout",
                    instructions="Rest" if offset == 6 else "Train moderately",
                    duration_minutes=None if offset == 6 else 40,
                ),
            )
            for offset in range(7)
        ]


class FailingPlanGenerator:
    def generate(self, *, start_date, context=None):
        raise AiProviderError("AI provider timed out")


def test_generate_plan_passes_bounded_context_to_ai_generator(auth_client):
    from app.api.plans import get_plan_generator
    from app.main import app

    headers = _auth_headers(auth_client)
    generator = RecordingPlanGenerator()
    app.dependency_overrides[get_plan_generator] = lambda: generator

    response = auth_client.post(
        "/api/plans/generate",
        headers=headers,
        json={"start_date": "2026-07-20", "title": "Context plan"},
    )

    assert response.status_code == 201
    assert generator.context is not None
    assert generator.context["today"] == "2026-07-20"
    assert "profile" in generator.context
    assert "current_plan" in generator.context
    assert "daily_summary" in generator.context
    assert "recent_messages" in generator.context
    assert "AI_API_KEY" not in str(generator.context)
    assert "password_hash" not in str(generator.context)


def test_generate_plan_provider_error_returns_502_and_preserves_current_plan(auth_client):
    from app.api.plans import get_plan_generator
    from app.main import app

    headers = _auth_headers(auth_client)
    existing = auth_client.post(
        "/api/plans/generate",
        headers=headers,
        json={"start_date": "2026-07-20", "title": "Existing"},
    )
    assert existing.status_code == 201
    existing_id = existing.json()["id"]
    app.dependency_overrides[get_plan_generator] = lambda: FailingPlanGenerator()

    no_raise_client = TestClient(auth_client.app, raise_server_exceptions=False)
    response = no_raise_client.post(
        "/api/plans/generate",
        headers=headers,
        json={"start_date": "2026-07-27", "title": "Fails"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider is unavailable"
    current = auth_client.get("/api/plans/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == existing_id
    assert current.json()["is_active"] is True
