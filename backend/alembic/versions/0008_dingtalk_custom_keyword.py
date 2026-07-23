"""add DingTalk custom robot keyword

Revision ID: 0008_dingtalk_custom_keyword
Revises: 0007_user_dingtalk_notifications
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_dingtalk_custom_keyword"
down_revision: str | None = "0007_user_dingtalk_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dingtalk_notifications",
        sa.Column("keyword", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dingtalk_notifications", "keyword")
