import json

import httpx

from app.core.config import Settings
from app.services.ai_client import OpenAICompatibleClient


async def test_chat_json_retries_without_unsupported_response_format():
    calls: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            return httpx.Response(400, json={"error": "response_format is not supported"}, request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]},
            request=request,
        )

    client = OpenAICompatibleClient(
        settings=Settings(
            database_url="sqlite+pysqlite:///:memory:",
            ai_base_url="https://example.test/v1",
            ai_api_key="test-key",
            ai_model="test-model",
        ),
        transport=httpx.MockTransport(handler),
    )

    assert await client.chat_json(system="return JSON", user="hello") == {"ok": True}
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]
