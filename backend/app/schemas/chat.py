from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from app.schemas.record import DailySummaryResponse, ExerciseLogResponse, FoodLogResponse


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2048)
    today: date | None = None


class PlanAdjustmentResponse(BaseModel):
    action: Literal["postpone_training", "replace_meal"]
    status: Literal["applied", "not_applicable", "failed"]
    plan_id: int | None = None
    source_date: date
    target_date: date | None = None
    meal_type: Literal["breakfast", "lunch", "snack", "dinner"] | None = None
    previous_meal_name: str | None = None
    updated_meal_name: str | None = None
    message: str

    @model_serializer(mode="wrap")
    def serialize_without_empty_meal_fields(self, handler):
        data = handler(self)
        if self.action != "replace_meal":
            data.pop("meal_type", None)
            data.pop("previous_meal_name", None)
            data.pop("updated_meal_name", None)
        return data


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    user_message_id: int
    user_created_at: datetime
    assistant_created_at: datetime
    recorded_food: FoodLogResponse | None = None
    recorded_exercise: ExerciseLogResponse | None = None
    daily_summary: DailySummaryResponse | None = None
    plan_adjustment: PlanAdjustmentResponse | None = None


class ChatHistoryMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    plan_adjustment: PlanAdjustmentResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryDeleteRequest(BaseModel):
    message_ids: list[int] = Field(min_length=1, max_length=100)


class ChatHistoryDeleteResponse(BaseModel):
    deleted_count: int


class NaturalLanguageRecordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2048)
    today: date | None = None


class NaturalLanguageFoodRecordResponse(BaseModel):
    # The dashboard keeps using this endpoint for backwards compatibility, but
    # the natural-language router can now return a pure exercise record too.
    record: FoodLogResponse | ExerciseLogResponse
    recorded_food: FoodLogResponse | None = None
    recorded_exercise: ExerciseLogResponse | None = None
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int


class NaturalLanguageExerciseRecordResponse(BaseModel):
    record: ExerciseLogResponse
    daily_summary: DailySummaryResponse
    adjustment_suggestion: str
    conversation_id: int
