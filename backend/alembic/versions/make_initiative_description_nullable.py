"""Make initiative description nullable

Revision ID: f7b8c9d0e1f2
Revises: e5f6a7b8c9d0
Create Date: 2026-02-20

Changes:
- Alter initiative.description column to allow NULL
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7b8c9d0e1f2'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('initiative', 'description', nullable=True)


def downgrade() -> None:
    # Set any NULLs to empty string before making NOT NULL again
    op.execute("UPDATE initiative SET description = '' WHERE description IS NULL")
    op.alter_column('initiative', 'description', nullable=False)
