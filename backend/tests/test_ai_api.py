import json

from datetime import date, datetime, timedelta

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


def test_food_natural_language_endpoint_splits_diet_and_exercise(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    goal = auth_client.put(
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
    assert goal.status_code == 200
    fake = FakeAiClient(
        json_responses=[
            {
                "diet": {
                    "description": "刚刚吃了两个烧烤",
                    "meal_type": "snack",
                    "logged_at": "2026-07-22T20:00:00+08:00",
                    "confidence": 0.78,
                    "items": [
                        {
                            "name": "烧烤串",
                            "quantity": "2串",
                            "calories": 200,
                            "protein_g": 12,
                            "carb_g": 10,
                            "fat_g": 12,
                        }
                    ],
                    "adjustment_suggestion": "后续注意补水。",
                },
                "exercise": {
                    "exercise_type": "慢跑",
                    "description": "慢跑了十分钟",
                    "duration_minutes": 10,
                    "calories_burned": 75,
                    "logged_at": "2026-07-22T20:00:00+08:00",
                    "confidence": 0.8,
                    "adjustment_suggestion": "属于短时轻中等强度有氧。",
                },
            }
        ]
    )
    app.dependency_overrides[get_ai_client] = lambda: fake

    response = auth_client.post(
        "/api/records/food/natural-language",
        headers=headers,
        json={
            "text": "刚刚吃了两个烧烤 慢跑了十分钟",
            "today": "2026-07-22",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["record"]["calories"] == 200
    assert body["recorded_exercise"]["calories_burned"] == 75
    assert body["daily_summary"]["food_totals"]["calories"] == 200
    assert body["daily_summary"]["exercise_totals"]["calories_burned"] == 75
    assert body["daily_summary"]["remaining_calories"] == 1875


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


def test_food_natural_language_endpoint_routes_pure_exercise_to_exercise_record(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    goal = auth_client.put(
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
    assert goal.status_code == 200
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClient(
        json_responses=[
            {
                "exercise_type": "running",
                "description": "慢跑 10 分钟",
                "duration_minutes": 10,
                "calories_burned": 80,
                "logged_at": "2026-07-23T08:30:00+08:00",
                "confidence": 0.9,
                "adjustment_suggestion": "运动后补充水分并做轻微拉伸?",
            }
        ]
    )

    response = auth_client.post(
        "/api/records/food/natural-language",
        headers=headers,
        json={"text": "我慢跑了", "today": "2026-07-23"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["recorded_food"] is None
    assert body["recorded_exercise"]["calories_burned"] == 80
    assert body["record"]["exercise_type"] == "running"
    assert body["daily_summary"]["food_totals"]["calories"] == 0
    assert body["daily_summary"]["exercise_totals"]["calories_burned"] == 80
    assert body["daily_summary"]["remaining_calories"] == 2080


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


def test_chat_history_returns_saved_successful_messages_in_chronological_order(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClient(text_responses=["晚餐增加一份蔬菜即可。"])

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "下午加餐后晚餐怎么安排？", "today": "2026-07-20"},
    )
    assert response.status_code == 200

    history = auth_client.get("/api/ai/history", headers=headers)
    assert history.status_code == 200
    body = history.json()
    assert [message["role"] for message in body] == ["user", "assistant"]
    assert [message["content"] for message in body] == ["下午加餐后晚餐怎么安排？", "晚餐增加一份蔬菜即可。"]


def test_chat_history_requires_authentication(auth_client):
    assert auth_client.get("/api/ai/history").status_code == 401


def test_chat_completed_exercise_is_saved_and_included_in_fatigue_context(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    fake = FakeAiClient(
        json_responses=[
            {
                "exercise_type": "腿部力量训练",
                "description": "深蹲和腿举 45 分钟，用户反馈腿很累",
                "duration_minutes": 45,
                "calories_burned": 310,
                "logged_at": "2026-07-22T18:40:00+08:00",
                "confidence": 0.88,
                "adjustment_suggestion": "今晚以恢复为主。",
            }
        ],
        text_responses=["已记录。今晚不要再练腿，优先补水、拉伸和睡眠。"],
    )
    app.dependency_overrides[get_ai_client] = lambda: fake

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "我刚练了45分钟腿，现在有点累", "today": "2026-07-22"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recorded_exercise"]["original_text"] == "我刚练了45分钟腿，现在有点累"
    assert body["recorded_exercise"]["calories_burned"] == 310
    assert body["daily_summary"]["exercise_totals"] == {
        "calories_burned": 310.0,
        "duration_minutes": 45.0,
    }
    assert len(body["daily_summary"]["exercise_records"]) == 1
    assert '"reported_fatigue": true' in fake.text_calls[0]["user"]
    assert "我刚练了45分钟腿，现在有点累" in fake.text_calls[0]["user"]

    daily = auth_client.get("/api/records/daily?date=2026-07-22", headers=headers)
    assert daily.status_code == 200
    assert daily.json()["exercise_totals"]["calories_burned"] == 310
    assert len(daily.json()["exercise_records"]) == 1


def test_mixed_record_detection_accepts_metrics_and_rejects_future_intent():
    from app.api.chat import looks_like_mixed_completed_records

    assert looks_like_mixed_completed_records("\u5403\u4e86\u4e00\u7897\u996d\u548c\u732a\u809d\uff0c\u722c\u576115\u5206\u949f\uff0c\u54c8\u514b\u6df1\u8e7230kg 4\u7ec4\u3002")
    assert not looks_like_mixed_completed_records("\u5348\u9910\u5403\u4e86\u4e00\u7897\u996d\uff0c\u4e0b\u5348\u60f3\u8dd1\u6b6515\u5206\u949f\u3002")
    assert not looks_like_mixed_completed_records("\u5348\u9910\u5403\u4e86\u4e00\u7897\u996d\uff0c\u4eca\u5929\u53ea\u80fd\u7ec320\u5206\u949f\u3002")


def test_chat_mixed_food_and_exercise_is_split_into_two_records(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    goal = auth_client.put(
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
    assert goal.status_code == 200
    fake = FakeAiClient(
        json_responses=[
            {
                "diet": {
                    "description": "中午吃了一碗饭和猪肝",
                    "meal_type": "lunch",
                    "logged_at": "2026-07-22T12:10:00+08:00",
                    "confidence": 0.86,
                    "items": [
                        {"name": "米饭", "quantity": "1碗", "calories": 260, "protein_g": 5, "carb_g": 58, "fat_g": 1},
                        {"name": "猪肝", "quantity": "120g", "calories": 200, "protein_g": 21, "carb_g": 8, "fat_g": 10},
                    ],
                    "adjustment_suggestion": "晚餐优先补充蔬菜和水分。",
                },
                "exercise": {
                    "exercise_type": "力量训练 + 有氧",
                    "description": "早上爬坡 15 分钟，哈克深蹲 30kg 4 组",
                    "duration_minutes": 35,
                    "calories_burned": 180,
                    "logged_at": "2026-07-22T08:20:00+08:00",
                    "confidence": 0.82,
                    "adjustment_suggestion": "今天不再追加腿部高强度训练。",
                },
            }
        ],
        text_responses=["已分别记录饮食和运动。"],
    )
    app.dependency_overrides[get_ai_client] = lambda: fake
    message = "中午吃了一碗饭和猪肝，早上爬坡15分钟，哈克深蹲30kg 4组。"

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": message, "today": "2026-07-22"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recorded_food"]["original_text"] == "中午吃了一碗饭和猪肝"
    assert body["recorded_food"]["calories"] == 460
    assert body["recorded_exercise"]["exercise_type"] == "力量训练 + 有氧"
    assert body["recorded_exercise"]["calories_burned"] == 180
    assert body["daily_summary"]["food_totals"]["calories"] == 460
    assert body["daily_summary"]["exercise_totals"]["calories_burned"] == 180
    assert body["daily_summary"]["remaining_calories"] == 1720
    assert len(body["daily_summary"]["food_records"]) == 1
    assert len(body["daily_summary"]["exercise_records"]) == 1
    assert "Split completed diet and exercise" in fake.json_calls[0]["user"]
    assert "MIXED" not in fake.text_calls[0]["user"]

    daily = auth_client.get("/api/records/daily?date=2026-07-22", headers=headers).json()
    assert daily["remaining_calories"] == 2000 - 460 + 180


def test_chat_does_not_save_future_or_negated_exercise(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    fake = FakeAiClient(text_responses=["可以安排。", "那就先恢复。", "可以压缩训练时间。"])
    app.dependency_overrides[get_ai_client] = lambda: fake

    future = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "我明天想跑步30分钟，怎么安排？", "today": "2026-07-22"},
    )
    negated = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "我今天没训练", "today": "2026-07-22"},
    )

    capability = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "我今天只能练20分钟", "today": "2026-07-22"},
    )

    assert future.status_code == 200
    assert negated.status_code == 200
    assert capability.status_code == 200
    assert future.json()["recorded_exercise"] is None
    assert negated.json()["recorded_exercise"] is None
    assert capability.json()["recorded_exercise"] is None
    assert fake.json_calls == []
    daily = auth_client.get("/api/records/daily?date=2026-07-22", headers=headers)
    assert daily.json()["exercise_records"] == []



def _adjustable_plan_payload(start: date) -> dict:
    days = []
    rest_indexes = {3, 6}
    for index in range(7):
        is_rest = index in rest_indexes
        days.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "calorie_target": 2100,
                "meals": [
                    {
                        "name": f"Meal {index + 1}",
                        "meal_type": "lunch",
                        "calories": 600,
                        "protein_g": 40,
                        "carb_g": 65,
                        "fat_g": 18,
                    }
                ],
                "training_instruction": {
                    "kind": "rest" if is_rest else "workout",
                    "title": f"Recovery {index + 1}" if is_rest else f"Workout {index + 1}",
                    "instructions": "Walk and stretch" if is_rest else "Complete the planned gym session",
                    "duration_minutes": None if is_rest else 45,
                },
            }
        )
    return {"title": "Adjustable week", "days": days}


def test_ai_chat_postpones_tomorrow_training_and_persists_confirmation(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    created = auth_client.post(
        "/api/plans",
        headers=headers,
        json=_adjustable_plan_payload(date(2026, 7, 22)),
    )
    assert created.status_code == 201
    original_days = created.json()["days"]
    original_tomorrow_title = original_days[1]["training_instruction"]["title"]
    following_title = original_days[2]["training_instruction"]["title"]

    fake = FakeAiClient(text_responses=["\u5df2\u7ecf\u5e2e\u4f60\u628a\u660e\u5929\u7684\u8bad\u7ec3\u987a\u5ef6\u4e00\u5929\u3002"])
    app.dependency_overrides[get_ai_client] = lambda: fake
    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={
            "message": "\u628a\u6211\u660e\u5929\u7684\u8bad\u7ec3\u8ba1\u5212\u5ef6\u8fdf\u4e00\u5929",
            "today": "2026-07-22",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan_adjustment"] == {
        "action": "postpone_training",
        "status": "applied",
        "plan_id": created.json()["id"],
        "source_date": "2026-07-23",
        "target_date": "2026-07-24",
        "message": "\u5df2\u5c067\u670823\u65e5\u7684\u8bad\u7ec3\u987a\u5ef6\u52307\u670824\u65e5\uff0c\u539f\u65e5\u671f\u5df2\u6539\u4e3a\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d\uff0c\u540e\u7eed\u8bad\u7ec3\u4e5f\u5df2\u4f9d\u6b21\u987a\u5ef6\u5e76\u4fdd\u5b58\u3002",
    }
    assert '"status": "applied"' in fake.text_calls[0]["user"]

    current = auth_client.get("/api/plans/current", headers=headers)
    assert current.status_code == 200
    updated_days = current.json()["days"]
    assert updated_days[1]["training_instruction"]["kind"] == "rest"
    assert updated_days[2]["training_instruction"]["title"] == original_tomorrow_title
    assert updated_days[3]["training_instruction"]["title"] == following_title
    assert updated_days[1]["meals"] == original_days[1]["meals"]

    history = auth_client.get("/api/ai/history", headers=headers).json()
    assert history[-1]["role"] == "assistant"
    assert history[-1]["plan_adjustment"]["status"] == "applied"
    assert history[0]["plan_adjustment"] is None


def test_ai_chat_explains_when_requested_day_is_already_a_rest_day(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    created = auth_client.post(
        "/api/plans",
        headers=headers,
        json=_adjustable_plan_payload(date(2026, 7, 20)),
    )
    assert created.status_code == 201
    # July 23 is index 3 and is intentionally a recovery day.
    fake = FakeAiClient(text_responses=["\u660e\u5929\u672c\u6765\u5c31\u662f\u6062\u590d\u65e5\u3002"])
    app.dependency_overrides[get_ai_client] = lambda: fake

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={
            "message": "\u628a\u660e\u5929\u7684\u8bad\u7ec3\u63a8\u8fdf\u4e00\u5929",
            "today": "2026-07-22",
        },
    )

    assert response.status_code == 200
    assert response.json()["plan_adjustment"]["status"] == "not_applicable"
    assert "\u6062\u590d\u65e5" in response.json()["plan_adjustment"]["message"]





def _meal_replacement_plan_payload(start_date: date):
    from datetime import timedelta

    meals = [
        {
            "name": "Oat egg breakfast",
            "meal_type": "breakfast",
            "calories": 500,
            "protein_g": 30,
            "carb_g": 55,
            "fat_g": 16,
            "foods": [{"name": "oats", "amount": "60g", "notes": None}, {"name": "eggs", "amount": "2", "notes": None}, {"name": "milk", "amount": "250ml", "notes": None}],
        },
        {
            "name": "Chicken rice lunch",
            "meal_type": "lunch",
            "calories": 650,
            "protein_g": 42,
            "carb_g": 72,
            "fat_g": 16,
            "foods": [{"name": "chicken", "amount": "150g", "notes": None}, {"name": "rice", "amount": "180g", "notes": None}, {"name": "broccoli", "amount": "200g", "notes": None}],
        },
        {
            "name": "Yogurt fruit snack",
            "meal_type": "snack",
            "calories": 300,
            "protein_g": 20,
            "carb_g": 35,
            "fat_g": 8,
            "foods": [{"name": "yogurt", "amount": "200g", "notes": None}, {"name": "banana", "amount": "1", "notes": None}, {"name": "nuts", "amount": "10g", "notes": None}],
        },
        {
            "name": "Original salmon dinner",
            "meal_type": "dinner",
            "calories": 700,
            "protein_g": 45,
            "carb_g": 60,
            "fat_g": 24,
            "foods": [{"name": "salmon", "amount": "150g", "notes": None}, {"name": "potato", "amount": "200g", "notes": None}, {"name": "lettuce", "amount": "150g", "notes": None}],
        },
    ]
    return {
        "title": "Partial adjustment test plan",
        "days": [
            {
                "date": (start_date + timedelta(days=index)).isoformat(),
                "calorie_target": 2150,
                "meals": meals,
                "training_instruction": {
                    "kind": "workout",
                    "title": f"Workout day {index + 1}",
                    "instructions": "Complete planned workout",
                    "duration_minutes": 45,
                    "split": "Upper A",
                    "focus": "Upper body",
                    "warmup": "Dynamic warmup",
                    "exercises": [],
                    "cooldown": "Stretch",
                },
            }
            for index in range(7)
        ],
    }


def test_ai_chat_replaces_only_requested_meal_and_preserves_the_rest(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    created = auth_client.post(
        "/api/plans",
        headers=headers,
        json=_meal_replacement_plan_payload(date(2026, 7, 23)),
    )
    assert created.status_code == 201
    original = created.json()

    fake = FakeAiClient(
        json_responses=[
            {
                "meal": {
                    "name": "Replacement tofu shrimp quinoa dinner",
                    "meal_type": "dinner",
                    "calories": 620,
                    "protein_g": 48,
                    "carb_g": 58,
                    "fat_g": 17,
                    "foods": [
                        {"name": "shrimp", "amount": "160g", "notes": None},
                        {"name": "tofu", "amount": "200g", "notes": None},
                        {"name": "quinoa", "amount": "120g", "notes": None},
                    ],
                }
            }
        ],
        text_responses=["Only tonight's dinner was replaced."],
    )
    app.dependency_overrides[get_ai_client] = lambda: fake
    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "\u628a\u4eca\u665a\u665a\u9910\u6362\u4e00\u4e0b", "today": "2026-07-23"},
    )

    assert response.status_code == 200
    adjustment = response.json()["plan_adjustment"]
    assert adjustment["action"] == "replace_meal"
    assert adjustment["status"] == "applied"
    assert adjustment["meal_type"] == "dinner"
    assert adjustment["previous_meal_name"] == "Original salmon dinner"
    assert adjustment["updated_meal_name"] == "Replacement tofu shrimp quinoa dinner"
    assert len(fake.json_calls) == 1
    replacement_context = json.loads(fake.json_calls[0]["user"])
    assert replacement_context["target_meal_type"] == "dinner"
    assert replacement_context["current_meal"]["name"] == "Original salmon dinner"

    current = auth_client.get("/api/plans/current", headers=headers).json()
    assert current["days"][0]["meals"][:3] == original["days"][0]["meals"][:3]
    assert current["days"][0]["meals"][3]["name"] == "Replacement tofu shrimp quinoa dinner"
    assert current["days"][0]["training_instruction"] == original["days"][0]["training_instruction"]
    assert current["days"][1:] == original["days"][1:]


def test_ai_chat_context_is_scoped_to_the_logged_in_user(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    owner_headers = _auth_headers(auth_client)
    fake = FakeAiClient(json_responses=[_food_result()], text_responses=["Received.", "Loaded the current account context."])
    app.dependency_overrides[get_ai_client] = lambda: fake
    food_response = auth_client.post(
        "/api/records/food/natural-language",
        headers=owner_headers,
        json={"text": "\u6211\u5403\u4e86\u53ea\u5c5e\u4e8eowner\u7684\u79d8\u5bc6\u65e9\u9910", "today": "2026-07-23"},
    )
    assert food_response.status_code == 201
    owner_chat = auth_client.post(
        "/api/ai/chat",
        headers=owner_headers,
        json={"message": "\u6839\u636e\u6211\u7684\u8bb0\u5f55\u7ed9\u5efa\u8bae", "today": "2026-07-23"},
    )
    assert owner_chat.status_code == 200
    owner_context = json.loads(fake.text_calls[-1]["user"])
    assert owner_context["recent_activity"]["food"][0]["original_text"] == "\u6211\u5403\u4e86\u53ea\u5c5e\u4e8eowner\u7684\u79d8\u5bc6\u65e9\u9910"
    assert owner_context["data_semantics"]["daily_summary"].startswith("actual records")

    auth_client.post("/api/auth/setup", json={"username": "second", "password": "another secure password"})
    second_token = auth_client.post(
        "/api/auth/login",
        json={"username": "second", "password": "another secure password"},
    ).json()["access_token"]
    second_chat = auth_client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"message": "\u6839\u636e\u6211\u7684\u8bb0\u5f55\u7ed9\u5efa\u8bae", "today": "2026-07-23"},
    )
    assert second_chat.status_code == 200
    second_context = json.loads(fake.text_calls[-1]["user"])
    assert second_context["account"]["username"] == "second"
    assert "\u53ea\u5c5e\u4e8eowner\u7684\u79d8\u5bc6\u65e9\u9910" not in fake.text_calls[-1]["user"]



def test_chat_response_and_history_use_persisted_user_timezone_timestamps(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    headers = _auth_headers(auth_client)
    profile = auth_client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Owner",
            "sex": "male",
            "birth_date": "2000-01-01",
            "height_cm": 175,
            "timezone": "Asia/Shanghai",
        },
    )
    assert profile.status_code == 200
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClient(text_responses=["Saved reply."])

    response = auth_client.post(
        "/api/ai/chat",
        headers=headers,
        json={"message": "How should I arrange dinner?", "today": "2026-07-23"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["user_message_id"], int)
    user_created_at = datetime.fromisoformat(body["user_created_at"])
    assistant_created_at = datetime.fromisoformat(body["assistant_created_at"])
    assert user_created_at.utcoffset() == timedelta(hours=8)
    assert assistant_created_at.utcoffset() == timedelta(hours=8)
    assert assistant_created_at >= user_created_at

    history = auth_client.get("/api/ai/history", headers=headers)
    assert history.status_code == 200
    saved = history.json()
    assert saved[0]["id"] == body["user_message_id"]
    assert saved[0]["created_at"] == body["user_created_at"]
    assert saved[1]["id"] == body["conversation_id"]
    assert saved[1]["created_at"] == body["assistant_created_at"]


def test_chat_history_delete_is_user_scoped_and_clear_preserves_health_records(auth_client):
    from app.api.ai import get_ai_client
    from app.main import app

    owner_headers = _auth_headers(auth_client)
    fake = FakeAiClient(text_responses=["Owner reply.", "Second reply."])
    app.dependency_overrides[get_ai_client] = lambda: fake

    food = auth_client.post(
        "/api/records/food",
        headers=owner_headers,
        json={
            "original_text": "Owner breakfast",
            "parsed_content": {"items": [{"name": "milk", "quantity": "1 bottle"}]},
            "meal_type": "breakfast",
            "calories": 180,
            "protein_g": 8,
            "carb_g": 20,
            "fat_g": 6,
            "logged_at": "2026-07-23T08:00:00+08:00",
        },
    )
    assert food.status_code == 201
    owner_chat = auth_client.post(
        "/api/ai/chat",
        headers=owner_headers,
        json={"message": "Owner chat message", "today": "2026-07-23"},
    )
    assert owner_chat.status_code == 200
    owner_body = owner_chat.json()

    auth_client.post("/api/auth/setup", json={"username": "second", "password": "another secure password"})
    second_token = auth_client.post(
        "/api/auth/login",
        json={"username": "second", "password": "another secure password"},
    ).json()["access_token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}
    second_chat = auth_client.post(
        "/api/ai/chat",
        headers=second_headers,
        json={"message": "Second user chat message", "today": "2026-07-23"},
    )
    assert second_chat.status_code == 200

    cross_user_delete = auth_client.post(
        "/api/ai/history/delete",
        headers=second_headers,
        json={"message_ids": [owner_body["conversation_id"]]},
    )
    assert cross_user_delete.status_code == 200
    assert cross_user_delete.json()["deleted_count"] == 0

    selected_delete = auth_client.post(
        "/api/ai/history/delete",
        headers=owner_headers,
        json={"message_ids": [owner_body["user_message_id"]]},
    )
    assert selected_delete.status_code == 200
    assert selected_delete.json()["deleted_count"] == 1
    owner_history = auth_client.get("/api/ai/history", headers=owner_headers).json()
    assert [message["id"] for message in owner_history] == [owner_body["conversation_id"]]

    clear_response = auth_client.delete("/api/ai/history", headers=owner_headers)
    assert clear_response.status_code == 200
    assert clear_response.json()["deleted_count"] == 1
    assert auth_client.get("/api/ai/history", headers=owner_headers).json() == []
    assert len(auth_client.get("/api/ai/history", headers=second_headers).json()) == 2

    daily = auth_client.get("/api/records/daily?date=2026-07-23", headers=owner_headers)
    assert daily.status_code == 200
    assert daily.json()["food_totals"]["calories"] == 180
    assert len(daily.json()["food_records"]) == 1


def test_chat_history_delete_requires_authentication(auth_client):
    assert auth_client.post("/api/ai/history/delete", json={"message_ids": [1]}).status_code == 401
    assert auth_client.delete("/api/ai/history").status_code == 401
