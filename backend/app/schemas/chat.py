from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.record import DailySummaryResponse, ExerciseLogResponse, FoodLogResponse


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2048)
    today: date | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int


class NaturalLanguageRecordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2048)
    today: date | None = None


class NaturalLanguageFoodRecordResponse(BaseModel):
    record: FoodLogResponse
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int


class NaturalLanguageExerciseRecordResponse(BaseModel):
    record: ExerciseLogResponse
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int
