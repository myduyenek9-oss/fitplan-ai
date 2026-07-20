"""enforce one active goal per user

Revision ID: 0003_goal_active_unique_index
Revises: 0002_profile_and_records
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_goal_active_unique_index"
down_revision: str | None = "0002_profile_and_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE goals
            SET is_active = false
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        row_number() OVER (
                            PARTITION BY user_id
                            ORDER BY updated_at DESC, id DESC
                        ) AS active_rank
                    FROM goals
                    WHERE is_active = true
                ) AS ranked_active_goals
                WHERE active_rank > 1
            )
            """
        )
    )
    op.create_index(
        "uq_goals_one_active_per_user",
        "goals",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_goals_one_active_per_user", table_name="goals")
