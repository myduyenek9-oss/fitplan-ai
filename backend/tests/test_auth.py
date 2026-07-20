from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_single_account_setup_can_only_initialize_once(auth_client):
    first_response = auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert first_response.status_code == 201
    assert first_response.json()["id"] == 1
    assert first_response.json()["username"] == "owner"
    assert "password_hash" not in first_response.json()

    second_response = auth_client.post(
        "/api/auth/setup",
        json={"username": "second", "password": "another secure password"},
    )
    assert second_response.status_code == 409


def test_setup_trims_and_normalizes_username(auth_client):
    response = auth_client.post(
        "/api/auth/setup",
        json={"username": "  Owner  ", "password": "correct horse battery staple"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "owner"


def test_login_returns_bearer_token_and_me_accepts_it(auth_client):
    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    login_response = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    assert login_response.status_code == 200
    token_body = login_response.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["access_token"]

    me_response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_body['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "owner"


def test_invalid_credentials_return_401(auth_client):
    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    response = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "wrong password"},
    )

    assert response.status_code == 401


def test_me_requires_valid_bearer_token(auth_client):
    response = auth_client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_tampered_malformed_expired_and_unknown_subject_tokens(auth_client):
    from app.core.security import create_access_token

    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    valid_token = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "correct horse battery staple"},
    ).json()["access_token"]
    tampered_token = f"{valid_token[:-1]}x"
    expired_token = create_access_token("1", expires_delta=timedelta(seconds=-1))
    unknown_subject_token = create_access_token("999")

    for token in [tampered_token, "not-a-jwt", expired_token, unknown_subject_token]:
        response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_me_rejects_non_strict_base64url_jwt_segments(auth_client):
    auth_client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    valid_token = auth_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "correct horse battery staple"},
    ).json()["access_token"]
    header, payload, signature = valid_token.split(".")
    malformed_tokens = [
        f"{valid_token}!!!!",
        f"{header}.{payload}.{signature}!!!!",
        f"{header}.{payload}.{signature}=",
        f"{header}.{payload}.A",
        f"{header}.{payload}.",
        f"{header}.{payload}.{signature}.extra",
        f"{header}.{payload}",
    ]

    for token in malformed_tokens:
        response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_decode_access_token_rejects_non_strict_base64url_segments(auth_client):
    from app.core.security import create_access_token, decode_access_token

    valid_token = create_access_token("1")
    header, payload, signature = valid_token.split(".")

    for token in [
        f"{valid_token}!!!!",
        f"{header}.{payload}.{signature}!!!!",
        f"{header}.{payload}.{signature}=",
        f"{header}.{payload}.A",
        f"{header}.{payload}.",
        f"{header}.{payload}.{signature}.extra",
        f"{header}.{payload}",
    ]:
        with pytest.raises(ValueError):
            decode_access_token(token)


def test_jwt_secret_must_be_configured_for_auth_operations(monkeypatch):
    from app.core.config import get_settings
    from app.core.security import create_access_token

    for value in [None, "replace-with-a-long-random-secret", "short-secret"]:
        monkeypatch.setenv("APP_ENV", "development")
        if value is None:
            monkeypatch.delenv("JWT_SECRET", raising=False)
        else:
            monkeypatch.setenv("JWT_SECRET", value)
        get_settings.cache_clear()

        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            create_access_token("1")

    get_settings.cache_clear()


def test_settings_cache_clear_applies_environment_overrides(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///first.db")
    monkeypatch.setenv("JWT_SECRET", "first-secret-with-at-least-32-characters")
    get_settings.cache_clear()
    assert get_settings().database_url == "sqlite+pysqlite:///first.db"

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///second.db")
    monkeypatch.setenv("JWT_SECRET", "second-secret-with-at-least-32-characters")
    get_settings.cache_clear()
    assert get_settings().database_url == "sqlite+pysqlite:///second.db"

    get_settings.cache_clear()


def test_user_table_enforces_singleton_user_at_database_layer():
    from app.db.base import Base
    from app.models.user import User

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        session.add(User(id=1, username="owner", password_hash="hash-one"))
        session.commit()
        session.add(User(id=2, username="intruder", password_hash="hash-two"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_password_hash_uses_argon2id_and_verifies():
    from app.core.security import hash_password, verify_password

    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert password_hash.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
