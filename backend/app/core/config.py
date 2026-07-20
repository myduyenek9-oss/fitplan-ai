from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fitplan:fitplan@localhost:5432/fitplan_ai"
    jwt_secret: str = "unsafe-development-secret-change-me"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
