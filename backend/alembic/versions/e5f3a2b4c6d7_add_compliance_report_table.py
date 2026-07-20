"""add compliance_report table

Revision ID: e5f3a2b4c6d7
Revises: d4e1f2a3b5c6
Create Date: 2026-02-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f3a2b4c6d7"
down_revision: str | None = "d4e1f2a3b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("total_answers", sa.Integer(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False),
        sa.Column("non_critical_count", sa.Integer(), nullable=False),
        sa.Column("compliant_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiative.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("initiative_id"),
    )
    op.create_index(
        op.f("ix_compliance_report_initiative_id"),
        "compliance_report",
        ["initiative_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_compliance_report_initiative_id"),
        table_name="compliance_report",
    )
    op.drop_table("compliance_report")
