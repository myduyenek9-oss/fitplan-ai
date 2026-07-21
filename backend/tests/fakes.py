from typing import Any


class FakeAiClient:
    def __init__(
        self,
        *,
        json_responses: list[dict[str, Any]] | None = None,
        text_responses: list[str] | None = None,
        json_error: Exception | None = None,
        text_error: Exception | None = None,
    ) -> None:
        self.json_responses = list(json_responses or [])
        self.text_responses = list(text_responses or [])
        self.json_error = json_error
        self.text_error = text_error
        self.json_calls: list[dict[str, str]] = []
        self.text_calls: list[dict[str, str]] = []

    async def chat_json(self, *, system: str, user: str) -> dict[str, Any]:
        self.json_calls.append({"system": system, "user": user})
        if self.json_error is not None:
            raise self.json_error
        if not self.json_responses:
            raise AssertionError("No fake JSON response queued")
        return self.json_responses.pop(0)

    async def chat_text(self, *, system: str, user: str) -> str:
        self.text_calls.append({"system": system, "user": user})
        if self.text_error is not None:
            raise self.text_error
        if not self.text_responses:
            raise AssertionError("No fake text response queued")
        return self.text_responses.pop(0)
