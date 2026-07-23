"""store per-user encrypted DingTalk notification settings

Revision ID: 0007_user_dingtalk_notifications
Revises: 0006_multi_user_accounts
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_user_dingtalk_notifications"
down_revision: str | None = "0006_multi_user_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dingtalk_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("webhook_encrypted", sa.String(length=4096), nullable=False),
        sa.Column("secret_encrypted", sa.String(length=2048), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_dingtalk_notifications_user_id"),
    )
    op.create_index("ix_dingtalk_notifications_user_id", "dingtalk_notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_dingtalk_notifications_user_id", table_name="dingtalk_notifications")
    op.drop_table("dingtalk_notifications")
