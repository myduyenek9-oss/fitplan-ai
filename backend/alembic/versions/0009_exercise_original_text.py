"""store original exercise input

Revision ID: 0009_exercise_original_text
Revises: 0008_dingtalk_custom_keyword
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_exercise_original_text"
down_revision: str | None = "0008_dingtalk_custom_keyword"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exercise_logs",
        sa.Column("original_text", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exercise_logs", "original_text")
