"""Assessment frozen dimension_scores snapshot column (HIST-02, gap-closure
plan 15-07).

Revision ID: k2b3c4d5e6f7
Revises: j1a2b3c4d5e6
Create Date: 2026-07-26

Adds a single nullable JSONB column, `dimension_scores`, to the `assessment`
table. This column is written exactly once, by `submit_initiative`, at the
moment an assessment flips from `draft` to `submitted` — it stores the
per-dimension scores computed by `compute_dimension_scores` against the
questionnaire config AS IT EXISTED AT SUBMISSION TIME.

Without this column, `list_assessment_history`/`_to_summary` always
recomputed scores live against whatever the CURRENT config happens to be,
so a later edit to the (explicitly placeholder, pending QSTN-05) config
would silently change every previously-submitted version's displayed
history — contradicting this phase's "permanently preserved assessment
version" guarantee. Freezing the snapshot here closes that gap.

This is a purely additive nullable column with NO unique constraint or
check constraint, so the WR-01 duplicate-row failure mode documented
against `j1a2b3c4d5e6`'s unique-constraint migration does not apply here.

Hand-written, not autogenerate, per this table's established migration
convention (i9d7e6f5a4b3, j1a2b3c4d5e6).

Downgrade: drops the column. Not lossy in any meaningful sense — this
column has no prior values to lose (it is new), and legacy submitted rows
already fall back to the live-recompute path when the column (or its value)
is absent.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "k2b3c4d5e6f7"
down_revision = "j1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment",
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment", "dimension_scores")
