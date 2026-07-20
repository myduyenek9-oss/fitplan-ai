from datetime import date as date_type, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, JSON, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.schemas.plan import MealPlan, WorkoutPlan


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        Index(
            "uq_plans_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    start_date: Mapped[date_type] = mapped_column(Date(), nullable=False)
    end_date: Mapped[date_type] = mapped_column(Date(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    days: Mapped[list["PlanDay"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanDay.date",
    )


class PlanDay(Base):
    __tablename__ = "plan_days"
    __table_args__ = (UniqueConstraint("plan_id", "date", name="uq_plan_days_plan_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date_type] = mapped_column(Date(), nullable=False)
    calorie_target: Mapped[float] = mapped_column(Float(), nullable=False)
    meals_json: Mapped[list[dict[str, Any]]] = mapped_column("meals", JSON(), nullable=False)
    training_instruction_json: Mapped[dict[str, Any]] = mapped_column(
        "training_instruction", JSON(), nullable=False
    )

    plan: Mapped[Plan] = relationship(back_populates="days")

    @property
    def meals(self) -> list[MealPlan]:
        return [MealPlan.model_validate(meal) for meal in self.meals_json]

    @property
    def training_instruction(self) -> WorkoutPlan:
        return WorkoutPlan.model_validate(self.training_instruction_json)
