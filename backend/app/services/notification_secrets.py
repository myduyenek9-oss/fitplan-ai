"""Encryption helpers for credentials saved in notification settings."""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class NotificationSecretError(RuntimeError):
    """Raised when encrypted notification credentials cannot be read safely."""


def _fernet() -> Fernet:
    settings = get_settings()
    configured_key = settings.notification_encryption_key
    material = configured_key.get_secret_value() if configured_key else ""
    if not material and settings.jwt_secret:
        material = settings.jwt_secret.get_secret_value()
    if not material:
        raise NotificationSecretError("Notification encryption is not configured")

    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_notification_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_notification_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise NotificationSecretError("Saved notification credentials cannot be decrypted") from exc
