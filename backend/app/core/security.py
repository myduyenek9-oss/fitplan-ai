import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings

_HASH_ALGORITHM = "pbkdf2_sha256"
_HASH_ITERATIONS = 210_000
_TOKEN_ALGORITHM = "HS256"
_DEFAULT_TOKEN_EXPIRES_MINUTES = 60 * 24


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
    )
    return "$".join(
        [
            _HASH_ALGORITHM,
            str(_HASH_ITERATIONS),
            _base64url_encode(salt),
            _base64url_encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != _HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _base64url_decode(salt_text)
        expected_digest = _base64url_decode(digest_text)
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=_DEFAULT_TOKEN_EXPIRES_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _encode_jwt(payload, get_settings().jwt_secret)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = _decode_jwt(token, get_settings().jwt_secret)
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token has expired")
    return payload


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
