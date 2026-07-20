from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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


def test_to_utc_storage_keeps_aware_utc_and_output_handles_legacy_naive_values():
    from zoneinfo import ZoneInfo

    from app.api.time_utils import to_utc_storage, utc_storage_to_timezone

    stored = to_utc_storage(datetime.fromisoformat("2026-07-20T00:30:00+08:00"))

    assert stored.tzinfo is UTC
    assert stored.isoformat() == "2026-07-19T16:30:00+00:00"
    assert utc_storage_to_timezone(stored, ZoneInfo("Asia/Shanghai")).isoformat() == (
        "2026-07-20T00:30:00+08:00"
    )
    assert utc_storage_to_timezone(
        datetime(2026, 7, 19, 16, 30), ZoneInfo("Asia/Shanghai")
    ).isoformat() == "2026-07-20T00:30:00+08:00"


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


def test_profile_responses_render_timestamps_in_profile_timezone(auth_client):
    headers = _auth_headers(auth_client)

    put_response = auth_client.put(
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
    get_response = auth_client.get("/api/profile", headers=headers)

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    for payload in (put_response.json(), get_response.json()):
        assert payload["created_at"].endswith("+08:00")
        assert payload["updated_at"].endswith("+08:00")


def test_goal_response_renders_timestamps_in_current_profile_timezone(auth_client):
    headers = _auth_headers(auth_client)
    auth_client.put(
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

    response = auth_client.put(
        "/api/profile/goal",
        headers=headers,
        json={
            "goal_type": "fat_loss",
            "daily_calories": 1800,
            "protein_g": 130,
            "carb_g": 180,
            "fat_g": 60,
            "activity_level": "moderate",
        },
    )

    assert response.status_code == 200
    goal = response.json()
    assert goal["created_at"].endswith("+08:00")
    assert goal["updated_at"].endswith("+08:00")


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
        {"weight_kg": 0, "logged_at": "2026-07-20T08:00:00Z"},
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


def test_profile_rejects_invalid_timezone(auth_client):
    headers = _auth_headers(auth_client)

    response = auth_client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Owner",
            "sex": "female",
            "birth_date": "1990-05-01",
            "height_cm": 168.5,
            "timezone": "Not/AZone",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        (
            "/api/profile",
            {
                "display_name": "Owner",
                "sex": "female",
                "birth_date": "1990-05-01",
                "height_cm": 0,
                "timezone": "UTC",
            },
        ),
        (
            "/api/profile",
            {
                "display_name": "Owner",
                "sex": "female",
                "birth_date": "2015-05-01",
                "height_cm": 168,
                "timezone": "UTC",
            },
        ),
        (
            "/api/profile/goal",
            {
                "goal_type": "fat_loss",
                "daily_calories": 0,
                "protein_g": 130,
                "carb_g": 180,
                "fat_g": 60,
                "activity_level": "moderate",
            },
        ),
        (
            "/api/profile/goal",
            {
                "goal_type": "fat_loss",
                "daily_calories": 1800,
                "protein_g": 0,
                "carb_g": 180,
                "fat_g": 60,
                "activity_level": "moderate",
            },
        ),
        (
            "/api/profile/goal",
            {
                "goal_type": "fat_loss",
                "daily_calories": 1800,
                "protein_g": 130,
                "carb_g": 180,
                "fat_g": 60,
                "activity_level": "moderate",
                "target_weight_kg": 0,
            },
        ),
    ],
)
def test_profile_and_goal_reject_obviously_invalid_ranges(auth_client, endpoint, payload):
    headers = _auth_headers(auth_client)

    response = auth_client.put(endpoint, headers=headers, json=payload)

    assert response.status_code == 422


def test_body_metric_logged_at_requires_timezone_offset(auth_client):
    headers = _auth_headers(auth_client)

    response = auth_client.post(
        "/api/body-metrics",
        headers=headers,
        json={"weight_kg": 70, "logged_at": "2026-07-20T08:00:00"},
    )

    assert response.status_code == 422


def test_body_metric_response_uses_profile_timezone(auth_client):
    headers = _auth_headers(auth_client)
    profile_response = auth_client.put(
        "/api/profile",
        headers=headers,
        json={
            "display_name": "Owner",
            "sex": "female",
            "birth_date": "1990-05-01",
            "height_cm": 168,
            "timezone": "Asia/Shanghai",
        },
    )

    create_response = auth_client.post(
        "/api/body-metrics",
        headers=headers,
        json={"weight_kg": 70, "logged_at": "2026-07-20T00:30:00+08:00"},
    )
    list_response = auth_client.get("/api/body-metrics", headers=headers)

    assert profile_response.status_code == 200
    assert create_response.status_code == 201
    assert create_response.json()["logged_at"].endswith("+08:00")
    assert list_response.status_code == 200
    assert list_response.json()[0]["logged_at"].endswith("+08:00")


def test_database_rejects_second_active_goal_for_same_user():
    from app.db.base import Base
    from app.models.goal import Goal
    from app.models.user import User

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.add(User(id=1, username="owner", password_hash="hash"))
        db.commit()
        db.add(
            Goal(
                user_id=1,
                goal_type="fat_loss",
                daily_calories=1800,
                protein_g=130,
                carb_g=180,
                fat_g=60,
                activity_level="moderate",
                is_active=True,
            )
        )
        db.commit()
        db.add(
            Goal(
                user_id=1,
                goal_type="maintenance",
                daily_calories=2200,
                protein_g=140,
                carb_g=260,
                fat_g=70,
                activity_level="active",
                is_active=True,
            )
        )

        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_active_goal_migration_keeps_latest_updated_at_then_id(monkeypatch):
    from app.core.config import get_settings

    temp_dir = Path(__file__).resolve().parents[2] / ".tmp_tests"
    temp_dir.mkdir(exist_ok=True)
    db_path = temp_dir / f"migration-{uuid4().hex}.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-with-at-least-32-characters")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

    command.upgrade(alembic_cfg, "0002_profile_and_records")
    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, username, password_hash) VALUES (1, 'owner', 'hash')")
        )
        connection.execute(
            text(
                """
                INSERT INTO goals (
                    id, user_id, goal_type, daily_calories, protein_g, carb_g, fat_g,
                    activity_level, is_active, created_at, updated_at
                ) VALUES
                    (10, 1, 'fat_loss', 1800, 130, 180, 60, 'moderate', 1,
                     '2026-07-20 00:00:00', '2026-07-20 11:00:00'),
                    (11, 1, 'maintenance', 2100, 140, 240, 70, 'active', 1,
                     '2026-07-20 00:00:00', '2026-07-20 09:00:00'),
                    (12, 1, 'muscle_gain', 2500, 160, 300, 80, 'active', 1,
                     '2026-07-20 00:00:00', '2026-07-20 10:00:00')
                """
            )
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, is_active FROM goals ORDER BY id")
        ).all()

    assert rows == [(10, 1), (11, 0), (12, 0)]

    engine.dispose()
    db_path.unlink(missing_ok=True)
    try:
        temp_dir.rmdir()
    except OSError:
        pass
    get_settings.cache_clear()
