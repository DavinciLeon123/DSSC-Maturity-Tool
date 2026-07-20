"""add questionnaire answers table

Revision ID: b3f7c9a1d2e8
Revises: c3f2a891e5b7
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f7c9a1d2e8"
down_revision: Union[str, None] = "c3f2a891e5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "questionnaire_answer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("answer_value", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiative.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("initiative_id", "question_id", name="uq_answer_per_question"),
    )
    op.create_index(op.f("ix_questionnaire_answer_initiative_id"), "questionnaire_answer", ["initiative_id"])
    op.create_index(op.f("ix_questionnaire_answer_question_id"), "questionnaire_answer", ["question_id"])
    op.create_index(op.f("ix_questionnaire_answer_mami_code"), "questionnaire_answer", ["mami_code"])


def downgrade() -> None:
    op.drop_index(op.f("ix_questionnaire_answer_mami_code"), table_name="questionnaire_answer")
    op.drop_index(op.f("ix_questionnaire_answer_question_id"), table_name="questionnaire_answer")
    op.drop_index(op.f("ix_questionnaire_answer_initiative_id"), table_name="questionnaire_answer")
    op.drop_table("questionnaire_answer")
