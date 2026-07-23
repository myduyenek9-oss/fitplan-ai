from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DingTalkNotification(Base):
    """One encrypted DingTalk robot configuration per FitPlan account."""

    __tablename__ = "dingtalk_notifications"
    __table_args__ = (UniqueConstraint("user_id", name="uq_dingtalk_notifications_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    webhook_encrypted: Mapped[str] = mapped_column(String(4096), nullable=False)
    secret_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
