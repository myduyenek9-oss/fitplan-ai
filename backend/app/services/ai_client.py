from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings


class AiProviderError(RuntimeError):
    """Raised when the configured AI provider cannot return usable output."""

    def __init__(self, message: str, *, response_format_unsupported: bool = False) -> None:
        super().__init__(message)
        self.response_format_unsupported = response_format_unsupported


class AiClient(Protocol):
    async def chat_json(self, *, system: str, user: str) -> dict[str, Any]: ...

    async def chat_text(self, *, system: str, user: str) -> str: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def chat_json(self, *, system: str, user: str) -> dict[str, Any]:
        try:
            content = await self._chat(system=system, user=user, response_format={"type": "json_object"})
        except AiProviderError as exc:
            # Some OpenAI-compatible providers reject response_format even though
            # they support the regular chat completions endpoint. Retry without
            # that optional parameter; the system prompt still requires JSON.
            if not exc.response_format_unsupported:
                raise
            content = await self._chat(system=system, user=user, response_format=None)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AiProviderError("AI provider returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise AiProviderError("AI provider returned invalid JSON")
        return parsed

    async def chat_text(self, *, system: str, user: str) -> str:
        return await self._chat(system=system, user=user, response_format=None)

    async def _chat(
        self,
        *,
        system: str,
        user: str,
        response_format: dict[str, str] | None,
    ) -> str:
        if not self.settings.ai_base_url or not self.settings.ai_api_key or not self.settings.ai_model:
            raise AiProviderError("AI provider is not configured")

        payload: dict[str, Any] = {
            "model": self.settings.ai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.ai_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AiProviderError("AI provider timed out") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise AiProviderError("AI provider access denied") from exc
            raise AiProviderError(
                "AI provider request failed",
                response_format_unsupported=(
                    response_format is not None and exc.response.status_code in {400, 404, 405, 415, 422}
                ),
            ) from exc
        except httpx.RequestError as exc:
            raise AiProviderError("AI provider is unavailable") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AiProviderError("AI provider returned an unexpected response") from exc
        if not isinstance(content, str) or not content.strip():
            raise AiProviderError("AI provider returned an empty response")
        return content
