from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index(
            "uq_goals_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    goal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    daily_calories: Mapped[float] = mapped_column(Float(), nullable=False)
    protein_g: Mapped[float] = mapped_column(Float(), nullable=False)
    carb_g: Mapped[float] = mapped_column(Float(), nullable=False)
    fat_g: Mapped[float] = mapped_column(Float(), nullable=False)
    activity_level: Mapped[str] = mapped_column(String(32), nullable=False)
    target_weight_kg: Mapped[float | None] = mapped_column(Float(), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False, index=True)
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
