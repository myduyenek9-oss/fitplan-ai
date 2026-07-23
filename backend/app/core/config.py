from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_database_url(database_url: str) -> str:
    """Resolve relative SQLite files from the repository root, not the process cwd."""
    url = make_url(database_url)
    database = url.database
    if (
        not url.drivername.startswith("sqlite")
        or not database
        or database == ":memory:"
        or database.startswith("file:")
        or Path(database).is_absolute()
    ):
        return database_url

    return str(url.set(database=str((PROJECT_ROOT / database).resolve())))


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fitplan:fitplan@localhost:5432/fitplan_ai"
    jwt_secret: SecretStr | None = None
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""
    notification_encryption_key: SecretStr | None = None
    dingtalk_daily_push_hour: int = Field(default=8, ge=0, le=23)
    dingtalk_daily_push_minute: int = Field(default=0, ge=0, le=59)
    app_env: str = "development"

    @field_validator("database_url")
    @classmethod
    def resolve_relative_sqlite_database_url(cls, value: str) -> str:
        return resolve_database_url(value)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
