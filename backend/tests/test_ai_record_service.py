from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.conversation import ConversationMessage
from app.models.record import ExerciseLog, FoodLog
from app.models.user import User
from app.services.ai_client import AiProviderError
from app.services.ai_record_service import AiRecordError, AiRecordService
from tests.fakes import FakeAiClient


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db_session):
    user = User(id=1, username="owner", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _food_ai_result():
    return {
        "meal_type": "snack",
        "logged_at": "2026-07-20T14:30:00+08:00",
        "confidence": 0.82,
        "items": [
            {
                "name": "鸡腿堡",
                "quantity": "1个",
                "calories": 520,
                "protein_g": 24,
                "carb_g": 50,
                "fat_g": 25,
            },
            {
                "name": "奶茶",
                "quantity": "1杯",
                "calories": 360,
                "protein_g": 5,
                "carb_g": 58,
                "fat_g": 11,
            },
        ],
        "adjustment_suggestion": "晚餐减少油脂和精制碳水，补充蔬菜与水。",
    }


@pytest.mark.asyncio
async def test_food_natural_language_creates_single_log_with_items_and_conversation(db_session, user):
    ai_client = FakeAiClient(json_responses=[_food_ai_result()])
    service = AiRecordService(ai_client=ai_client)

    result = await service.create_food_from_text(
        db_session,
        user_id=user.id,
        text="刚才吃了一个鸡腿堡和一杯奶茶",
        today=date(2026, 7, 20),
    )

    assert result.record.original_text == "刚才吃了一个鸡腿堡和一杯奶茶"
    assert result.record.calories == 880
    assert result.record.protein_g == 29
    assert result.record.carb_g == 108
    assert result.record.fat_g == 36
    assert result.record.parsed_content["confidence"] == 0.82
    assert [item["name"] for item in result.record.parsed_content["items"]] == ["鸡腿堡", "奶茶"]
    assert result.daily_summary.food_totals.calories == 880
    assert result.adjustment_suggestion == "晚餐减少油脂和精制碳水，补充蔬菜与水。"

    food_logs = list(db_session.scalars(select(FoodLog)))
    assert len(food_logs) == 1
    messages = list(db_session.scalars(select(ConversationMessage)))
    assert len(messages) == 2
    assert messages[0].source == "food_natural_language"
    assert messages[0].content == "刚才吃了一个鸡腿堡和一杯奶茶"
    assert messages[1].metadata_json["record_id"] == result.record.id


@pytest.mark.asyncio
async def test_food_invalid_ai_result_keeps_audit_message_and_writes_no_record(db_session, user):
    ai_client = FakeAiClient(json_responses=[{"items": []}])
    service = AiRecordService(ai_client=ai_client)

    with pytest.raises(AiRecordError, match="AI returned invalid food data"):
        await service.create_food_from_text(
            db_session,
            user_id=user.id,
            text="刚才吃了一个鸡腿堡和一杯奶茶",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(FoodLog))) == []
    messages = list(db_session.scalars(select(ConversationMessage)))
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].source == "food_natural_language"
    assert messages[0].metadata_json["status"] == "failed"


@pytest.mark.asyncio
async def test_provider_error_writes_no_partial_food_log(db_session, user):
    service = AiRecordService(
        ai_client=FakeAiClient(json_error=AiProviderError("AI provider timed out"))
    )

    with pytest.raises(AiRecordError, match="AI provider timed out"):
        await service.create_food_from_text(
            db_session,
            user_id=user.id,
            text="加餐薯片一包",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(FoodLog))) == []


@pytest.mark.asyncio
async def test_exercise_natural_language_creates_exercise_log_and_conversation(db_session, user):
    ai_client = FakeAiClient(
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
    service = AiRecordService(ai_client=ai_client)

    result = await service.create_exercise_from_text(
        db_session,
        user_id=user.id,
        text="晚上慢跑了30分钟",
        today=date(2026, 7, 20),
    )

    assert result.record.exercise_type == "running"
    assert result.record.duration_minutes == 30
    assert result.record.calories_burned == 240
    assert result.daily_summary.exercise_totals.calories_burned == 240
    assert len(list(db_session.scalars(select(ExerciseLog)))) == 1
    assert len(list(db_session.scalars(select(ConversationMessage)))) == 2




def _plan_ai_result():
    days = []
    for offset in range(7):
        day = date(2026, 7, 20).toordinal() + offset
        day_date = date.fromordinal(day).isoformat()
        days.append(
            {
                "date": day_date,
                "calorie_target": 1900 + offset,
                "meals": [
                    {
                        "name": f"AI meal {offset + 1}",
                        "meal_type": "lunch",
                        "calories": 600,
                        "protein_g": 35,
                        "carb_g": 65,
                        "fat_g": 18,
                    }
                ],
                "training_instruction": {
                    "kind": "rest" if offset == 6 else "workout",
                    "title": "Recovery" if offset == 6 else "AI workout",
                    "instructions": "Rest and walk" if offset == 6 else "Moderate strength session",
                    "duration_minutes": None if offset == 6 else 40,
                },
            }
        )
    return {"title": "AI plan", "days": days, "safety_note": "???????????"}


def test_ai_plan_generator_uses_same_json_client_and_validates_seven_days():
    from app.services.plan_service import AiPlanGenerator

    fake = FakeAiClient(json_responses=[_plan_ai_result()])
    generator = AiPlanGenerator(ai_client=fake)

    days = generator.generate(start_date=date(2026, 7, 20))

    assert len(days) == 7
    assert days[0].date == date(2026, 7, 20)
    assert days[0].meals[0].name == "AI meal 1"
    assert days[6].training_instruction.kind == "rest"
    assert "JSON only" in fake.json_calls[0]["system"]
    assert "2026-07-20" in fake.json_calls[0]["user"]



@pytest.mark.asyncio
async def test_openai_compatible_client_rejects_invalid_json_without_network(monkeypatch):
    import httpx

    from app.core.config import get_settings
    from app.services.ai_client import OpenAICompatibleClient

    monkeypatch.setenv("AI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.invalid/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    client = OpenAICompatibleClient(
        settings=get_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(AiProviderError, match="invalid JSON"):
        await client.chat_json(system="Return JSON only", user="{}")

    get_settings.cache_clear()


def test_openai_compatible_client_requires_provider_settings(monkeypatch):
    from app.core.config import get_settings
    from app.services.ai_client import OpenAICompatibleClient

    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    get_settings.cache_clear()

    client = OpenAICompatibleClient(settings=get_settings())

    with pytest.raises(AiProviderError, match="not configured"):
        import asyncio

        asyncio.run(client.chat_text(system="safe", user="hello"))

    get_settings.cache_clear()
