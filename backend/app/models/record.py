from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float(), nullable=True)
    body_fat_percent: Mapped[float | None] = mapped_column(Float(), nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float(), nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Float(), nullable=True)
    hip_cm: Mapped[float | None] = mapped_column(Float(), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class FoodLog(Base):
    __tablename__ = "food_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    original_text: Mapped[str] = mapped_column(String(2048), nullable=False)
    parsed_content: Mapped[dict[str, Any]] = mapped_column(JSON(), default=dict, nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calories: Mapped[float] = mapped_column(Float(), nullable=False)
    protein_g: Mapped[float] = mapped_column(Float(), nullable=False)
    carb_g: Mapped[float] = mapped_column(Float(), nullable=False)
    fat_g: Mapped[float] = mapped_column(Float(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    original_text: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    exercise_type: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_minutes: Mapped[float] = mapped_column(Float(), nullable=False)
    calories_burned: Mapped[float] = mapped_column(Float(), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
