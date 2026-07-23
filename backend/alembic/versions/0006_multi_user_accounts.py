"""allow multiple FitPlan accounts

Revision ID: 0006_multi_user_accounts
Revises: 0005_conversations
Create Date: 2026-07-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_multi_user_accounts"
down_revision: str | None = "0005_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text("PRAGMA foreign_keys=OFF"))
        try:
            with op.batch_alter_table("users", recreate="always") as batch_op:
                batch_op.drop_constraint("ck_users_singleton_id", type_="check")
        finally:
            bind.execute(sa.text("PRAGMA foreign_keys=ON"))
        return

    op.drop_constraint("ck_users_singleton_id", "users", type_="check")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text("PRAGMA foreign_keys=OFF"))
        try:
            with op.batch_alter_table("users", recreate="always") as batch_op:
                batch_op.create_check_constraint("ck_users_singleton_id", "id = 1")
        finally:
            bind.execute(sa.text("PRAGMA foreign_keys=ON"))
        return

    op.create_check_constraint("ck_users_singleton_id", "users", "id = 1")
