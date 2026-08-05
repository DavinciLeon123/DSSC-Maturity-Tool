"""Add data_consent column to user table

Revision ID: l3c4d5e6f7a8
Revises: k2b3c4d5e6f7
Create Date: 2026-08-05

Changes:
- Add data_consent column to user (BOOLEAN, NOT NULL, server_default=true)
- Single-step ADD COLUMN NOT NULL DEFAULT — Postgres backfills every
  existing row atomically as part of the ALTER TABLE. No separate
  UPDATE, no nullable-relax/reinstate two-step (see
  add_user_participant_type.py, e5f6a7b8c9d0, the correct precedent —
  NOT i9d7e6f5a4b3, which solves the opposite problem).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "l3c4d5e6f7a8"
down_revision = "k2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("data_consent", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("user", "data_consent")
