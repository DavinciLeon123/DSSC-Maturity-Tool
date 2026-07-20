"""add evidence_url table

Revision ID: d4e1f2a3b5c6
Revises: b3f7c9a1d2e8
Create Date: 2026-02-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e1f2a3b5c6"
down_revision: str | None = "b3f7c9a1d2e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_url",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiative.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_url_initiative_id"), "evidence_url", ["initiative_id"])
    op.create_index(op.f("ix_evidence_url_question_id"), "evidence_url", ["question_id"])
    op.create_index(op.f("ix_evidence_url_mami_code"), "evidence_url", ["mami_code"])


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_url_mami_code"), table_name="evidence_url")
    op.drop_index(op.f("ix_evidence_url_question_id"), table_name="evidence_url")
    op.drop_index(op.f("ix_evidence_url_initiative_id"), table_name="evidence_url")
    op.drop_table("evidence_url")
