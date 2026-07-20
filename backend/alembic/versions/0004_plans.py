"""add versioned seven-day plans

Revision ID: 0004_plans
Revises: 0003_goal_active_unique_index
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_plans"
down_revision: str | None = "0003_goal_active_unique_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])
    op.create_index("ix_plans_is_active", "plans", ["is_active"])
    op.create_index(
        "uq_plans_one_active_per_user",
        "plans",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "plan_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("calorie_target", sa.Float(), nullable=False),
        sa.Column("meals", sa.JSON(), nullable=False),
        sa.Column("training_instruction", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "date", name="uq_plan_days_plan_date"),
    )
    op.create_index("ix_plan_days_plan_id", "plan_days", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_days_plan_id", table_name="plan_days")
    op.drop_table("plan_days")
    op.drop_index("uq_plans_one_active_per_user", table_name="plans")
    op.drop_index("ix_plans_is_active", table_name="plans")
    op.drop_index("ix_plans_user_id", table_name="plans")
    op.drop_table("plans")
