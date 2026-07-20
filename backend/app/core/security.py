import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import get_settings

_TOKEN_ALGORITHM = "HS256"
_DEFAULT_TOKEN_EXPIRES_MINUTES = 60 * 24
_MIN_JWT_SECRET_LENGTH = 32
_PLACEHOLDER_JWT_SECRETS = {
    "replace-with-a-long-random-secret",
    "unsafe-development-secret-change-me",
}
_password_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)


class AuthConfigurationError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, VerifyMismatchError):
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=_DEFAULT_TOKEN_EXPIRES_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _encode_jwt(payload, _get_jwt_secret())


def decode_access_token(token: str) -> dict[str, Any]:
    payload = _decode_jwt(token, _get_jwt_secret())
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token has expired")
    return payload


def _get_jwt_secret() -> str:
    configured_secret = get_settings().jwt_secret
    secret = configured_secret.get_secret_value().strip() if configured_secret is not None else ""
    if (
        not secret
        or len(secret) < _MIN_JWT_SECRET_LENGTH
        or secret.lower() in _PLACEHOLDER_JWT_SECRETS
    ):
        raise AuthConfigurationError(
            "JWT_SECRET must be set to a non-placeholder value with at least "
            f"{_MIN_JWT_SECRET_LENGTH} characters"
        )
    return secret


def _encode_jwt(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": _TOKEN_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        [
            _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def _decode_jwt(token: str, secret: str) -> dict[str, Any]:
    try:
        header_text, payload_text, signature_text = token.split(".", 2)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{header_text}.{payload_text}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        supplied_signature = _base64url_decode(signature_text)
    except ValueError as exc:
        raise ValueError("Invalid token signature") from exc
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("Invalid token signature")

    try:
        header = json.loads(_base64url_decode(header_text))
        payload = json.loads(_base64url_decode(payload_text))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Invalid token payload") from exc

    if header.get("alg") != _TOKEN_ALGORITHM or header.get("typ") != "JWT":
        raise ValueError("Unsupported token type")
    if not isinstance(payload, dict):
        raise ValueError("Invalid token payload")
    return payload


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
