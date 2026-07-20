"""DSI/SP questionnaire foundation: participant_type on initiative, new answer values, followup fields

Revision ID: f6a4b3c2d1e9
Revises: e5f3a2b4c6d7
Create Date: 2026-02-19

Changes:
- Add participant_type column to initiative (VARCHAR 'DSI'|'SP', default 'DSI')
- Add followup_selections (JSONB) and followup_other (TEXT) to questionnaire_answer
- Migrate existing answer_value: NO/COMPLY_EXPLAIN -> NOT_THERE_YET (VARCHAR — no enum type change)
  (rationale text preserved in followup_other for COMPLY_EXPLAIN answers)
- Keep rationale column as nullable (deprecated, not dropped for data safety)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a4b3c2d1e9"
down_revision = "e5f3a2b4c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add participant_type to initiative (VARCHAR — matches SQLModel string enum storage)
    op.add_column(
        "initiative",
        sa.Column("participant_type", sa.String(), nullable=False, server_default="DSI"),
    )

    # 2. Add followup columns to questionnaire_answer
    op.add_column("questionnaire_answer", sa.Column("followup_selections", JSONB, nullable=True))
    op.add_column("questionnaire_answer", sa.Column("followup_other", sa.Text, nullable=True))

    # 3. Preserve rationale as followup_other for old COMPLY_EXPLAIN answers
    op.execute("""
        UPDATE questionnaire_answer
        SET followup_other = rationale
        WHERE answer_value = 'COMPLY_EXPLAIN'
          AND rationale IS NOT NULL
    """)

    # 4. Migrate NO and COMPLY_EXPLAIN -> NOT_THERE_YET (answer_value is VARCHAR — direct UPDATE)
    op.execute("""
        UPDATE questionnaire_answer
        SET answer_value = 'NOT_THERE_YET'
        WHERE answer_value IN ('NO', 'COMPLY_EXPLAIN')
    """)


def downgrade() -> None:
    # Reverse answer value migration (loses distinction between old NO and COMPLY_EXPLAIN)
    op.execute("""
        UPDATE questionnaire_answer
        SET answer_value = 'NO'
        WHERE answer_value = 'NOT_THERE_YET'
    """)
    op.drop_column("questionnaire_answer", "followup_other")
    op.drop_column("questionnaire_answer", "followup_selections")
    op.drop_column("initiative", "participant_type")
