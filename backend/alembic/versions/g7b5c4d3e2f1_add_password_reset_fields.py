"""Add password reset fields to user table

Revision ID: g7b5c4d3e2f1
Revises: f7b8c9d0e1f2
Create Date: 2026-03-05

Changes:
- Add nullable password_reset_token column to user table
- Add nullable password_reset_expires column to user table
"""

import sqlalchemy as sa

from alembic import op

revision = "g7b5c4d3e2f1"
down_revision = "f7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("password_reset_token", sa.String(), nullable=True))
    op.add_column("user", sa.Column("password_reset_expires", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "password_reset_expires")
    op.drop_column("user", "password_reset_token")
