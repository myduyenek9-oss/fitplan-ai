from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.conversation import ConversationMessage
from app.models.record import ExerciseLog, FoodLog
from app.models.user import User
from app.services.ai_client import AiProviderError
from app.services.ai_record_service import AiRecordError, AiRecordService, _resolve_recorded_at
from tests.fakes import FakeAiClient


def test_record_time_uses_exact_submission_minute_when_text_has_no_clock_time():
    timezone = ZoneInfo("Asia/Shanghai")
    resolved = _resolve_recorded_at(
        text="just ate a banana",
        parsed_logged_at=datetime(2026, 7, 22, 19, 0, tzinfo=timezone),
        day=date(2026, 7, 22),
        user_timezone=timezone,
        now=datetime(2026, 7, 22, 19, 58, 42, tzinfo=timezone),
    )

    assert resolved == datetime(2026, 7, 22, 11, 58, 42, tzinfo=UTC)


def test_record_time_keeps_explicit_hour_and_minute_from_text():
    timezone = ZoneInfo("Asia/Shanghai")
    parsed_time = datetime(2026, 7, 22, 8, 35, tzinfo=timezone)

    resolved = _resolve_recorded_at(
        text="ate breakfast at 8:35",
        parsed_logged_at=parsed_time,
        day=date(2026, 7, 22),
        user_timezone=timezone,
        now=datetime(2026, 7, 22, 19, 58, 42, tzinfo=timezone),
    )

    assert resolved == datetime(2026, 7, 22, 0, 35, tzinfo=UTC)


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
async def test_food_quick_record_splits_completed_diet_and_exercise(db_session, user):
    ai_client = FakeAiClient(
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
    service = AiRecordService(ai_client=ai_client)

    result = await service.create_food_from_text(
        db_session,
        user_id=user.id,
        text="刚刚吃了两个烧烤 慢跑了十分钟",
        today=date(2026, 7, 22),
    )

    assert result.record.original_text == "刚刚吃了两个烧烤"
    assert result.record.calories == 200
    assert result.recorded_exercise is not None
    assert result.recorded_exercise.duration_minutes == 10
    assert result.recorded_exercise.calories_burned == 75
    assert result.daily_summary.food_totals.calories == 200
    assert result.daily_summary.exercise_totals.calories_burned == 75
    assert len(result.daily_summary.exercise_records) == 1

    assert len(list(db_session.scalars(select(FoodLog)))) == 1
    assert len(list(db_session.scalars(select(ExerciseLog)))) == 1
    messages = list(db_session.scalars(select(ConversationMessage)))
    assert messages[-1].metadata_json["record_types"] == ["food", "exercise"]


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
async def test_food_ai_result_rejects_blank_optional_meal_type_and_writes_no_record(db_session, user):
    result = _food_ai_result()
    result["meal_type"] = "   "
    service = AiRecordService(ai_client=FakeAiClient(json_responses=[result]))

    with pytest.raises(AiRecordError, match="AI returned invalid food data"):
        await service.create_food_from_text(
            db_session,
            user_id=user.id,
            text="extra burger",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(FoodLog))) == []
    assert list(db_session.scalars(select(ConversationMessage)))[0].metadata_json["status"] == "failed"


@pytest.mark.asyncio
async def test_food_ai_result_rejects_blank_item_name_and_writes_no_record(db_session, user):
    result = _food_ai_result()
    result["items"][0]["name"] = "   "
    service = AiRecordService(ai_client=FakeAiClient(json_responses=[result]))

    with pytest.raises(AiRecordError, match="AI returned invalid food data"):
        await service.create_food_from_text(
            db_session,
            user_id=user.id,
            text="extra burger",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(FoodLog))) == []
    assert list(db_session.scalars(select(ConversationMessage)))[0].metadata_json["status"] == "failed"


@pytest.mark.asyncio
async def test_food_ai_result_rejects_unreasonable_calories_and_writes_no_record(db_session, user):
    result = _food_ai_result()
    result["items"][0]["calories"] = 1_000_000
    service = AiRecordService(ai_client=FakeAiClient(json_responses=[result]))

    with pytest.raises(AiRecordError, match="AI returned invalid food data"):
        await service.create_food_from_text(
            db_session,
            user_id=user.id,
            text="extra burger",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(FoodLog))) == []
    assert list(db_session.scalars(select(ConversationMessage)))[0].metadata_json["status"] == "failed"


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

@pytest.mark.asyncio
async def test_exercise_ai_result_rejects_blank_optional_description_and_writes_no_record(db_session, user):
    service = AiRecordService(
        ai_client=FakeAiClient(
            json_responses=[
                {
                    "exercise_type": "running",
                    "description": "   ",
                    "duration_minutes": 30,
                    "calories_burned": 240,
                    "logged_at": "2026-07-20T19:30:00+08:00",
                    "confidence": 0.9,
                    "adjustment_suggestion": "hydrate.",
                }
            ]
        )
    )

    with pytest.raises(AiRecordError, match="AI returned invalid exercise data"):
        await service.create_exercise_from_text(
            db_session,
            user_id=user.id,
            text="ran 30 minutes",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(ExerciseLog))) == []
    assert list(db_session.scalars(select(ConversationMessage)))[0].metadata_json["status"] == "failed"


@pytest.mark.asyncio
async def test_exercise_ai_result_rejects_unreasonable_duration_and_writes_no_record(db_session, user):
    service = AiRecordService(
        ai_client=FakeAiClient(
            json_responses=[
                {
                    "exercise_type": "running",
                    "description": "run",
                    "duration_minutes": 100_000,
                    "calories_burned": 240,
                    "logged_at": "2026-07-20T19:30:00+08:00",
                    "confidence": 0.9,
                    "adjustment_suggestion": "hydrate.",
                }
            ]
        )
    )

    with pytest.raises(AiRecordError, match="AI returned invalid exercise data"):
        await service.create_exercise_from_text(
            db_session,
            user_id=user.id,
            text="ran 30 minutes",
            today=date(2026, 7, 20),
        )

    assert list(db_session.scalars(select(ExerciseLog))) == []
    assert list(db_session.scalars(select(ConversationMessage)))[0].metadata_json["status"] == "failed"





def _plan_ai_result():
    days = []
    for offset in range(7):
        day_date = date.fromordinal(date(2026, 7, 20).toordinal() + offset).isoformat()
        meals = [
            {
                "name": f"AI meal {offset + 1}",
                "meal_type": meal_type,
                "calories": 475,
                "protein_g": 30,
                "carb_g": 50,
                "fat_g": 12,
                "foods": [
                    {"name": "Food A", "amount": "100g"},
                    {"name": "Food B", "amount": "150g"},
                    {"name": "Food C", "amount": "1 serving"},
                ],
            }
            for meal_type in ["breakfast", "lunch", "snack", "dinner"]
        ]
        training = {
            "kind": "rest" if offset == 6 else "workout",
            "title": "Recovery" if offset == 6 else "AI workout",
            "instructions": "Rest and walk" if offset == 6 else "Moderate strength session",
            "duration_minutes": None if offset == 6 else 40,
            "split": "Recovery" if offset == 6 else "Upper/lower split",
            "focus": "Recovery" if offset == 6 else "Technique",
            "warmup": None if offset == 6 else "Walk for five minutes",
            "exercises": [] if offset == 6 else [
                {"name": f"Exercise {number}", "sets": 3, "reps": "8-12", "rest_seconds": 90, "notes": "Controlled form"}
                for number in range(1, 6)
            ],
            "cooldown": "Stretch",
        }
        days.append({"date": day_date, "calorie_target": 1900 + offset, "meals": meals, "training_instruction": training})
    return {"title": "AI plan", "days": days, "safety_note": "safe balanced plan"}


def test_ai_plan_generator_uses_same_json_client_and_bounded_context():
    from app.services.plan_service import AiPlanGenerator

    fake = FakeAiClient(json_responses=[_plan_ai_result()])
    generator = AiPlanGenerator(ai_client=fake)

    days = generator.generate(
        start_date=date(2026, 7, 20),
        context={
            "profile": {"height_cm": 180},
            "current_plan": {"title": "Current"},
            "daily_summary": {"food_totals": {"calories": 880}},
            "recent_messages": [{"role": "user", "content": "fat loss goal"}],
        },
    )

    assert len(days) == 7
    assert days[0].date == date(2026, 7, 20)
    assert days[0].meals[0].name == "AI meal 1"
    assert days[6].training_instruction.kind == "rest"
    assert "JSON only" in fake.json_calls[0]["system"]
    assert "2026-07-20" in fake.json_calls[0]["user"]
    assert "height_cm" in fake.json_calls[0]["user"]
    assert "fat loss goal" in fake.json_calls[0]["user"]
    assert "AI_API_KEY" not in fake.json_calls[0]["user"]



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
    from app.core.config import Settings, get_settings
    from app.services.ai_client import OpenAICompatibleClient

    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    get_settings.cache_clear()

    client = OpenAICompatibleClient(settings=get_settings())

    with pytest.raises(AiProviderError, match="not configured"):
        import asyncio

        asyncio.run(client.chat_text(system="safe", user="hello"))

    get_settings.cache_clear()
