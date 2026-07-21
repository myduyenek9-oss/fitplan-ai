from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.ai_client import AiClient, OpenAICompatibleClient


def get_ai_client(settings: Settings = Depends(get_settings)) -> AiClient:
    return OpenAICompatibleClient(settings=settings)
