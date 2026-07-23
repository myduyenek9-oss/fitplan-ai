from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DingTalkNotificationUpsert(BaseModel):
    webhook: str = Field(min_length=20, max_length=2048)
    secret: str | None = Field(default=None, max_length=512)
    keyword: str | None = Field(default=None, max_length=128)
    is_enabled: bool = True

    @field_validator("webhook")
    @classmethod
    def validate_webhook(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("DingTalk webhook must be a valid HTTPS URL")
        return normalized

    @field_validator("secret", "keyword")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.replace("\r", " ").replace("\n", " ").strip() or None


class DingTalkNotificationResponse(BaseModel):
    is_configured: bool
    is_enabled: bool
    webhook_hint: str | None = None
    has_signing_secret: bool = False
    keyword: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DingTalkTestPushResponse(BaseModel):
    delivered: bool = True
