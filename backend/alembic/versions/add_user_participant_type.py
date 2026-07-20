"""Add participant_type column to user table

Revision ID: e5f6a7b8c9d0
Revises: f6a4b3c2d1e9
Create Date: 2026-02-20

Changes:
- Add participant_type column to user (VARCHAR 'DSI'|'SP', server_default='DSI')
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'f6a4b3c2d1e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column('participant_type', sa.String(), nullable=False, server_default='DSI')
    )


def downgrade() -> None:
    op.drop_column('user', 'participant_type')
