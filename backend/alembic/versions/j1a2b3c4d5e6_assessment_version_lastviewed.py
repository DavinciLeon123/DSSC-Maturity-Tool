"""Assessment version-uniqueness constraint + last_viewed_category_id column
(D-08, D-15/HIST-01, Pitfall 4)

Revision ID: j1a2b3c4d5e6
Revises: i9d7e6f5a4b3
Create Date: 2026-07-25

Bundles two independent, additive changes to the `assessment` table (both
touch the same table, so they are shipped in one hand-written migration
following the i9d7e6f5a4b3 precedent rather than two separate ones):

1. `uq_assessment_version_per_initiative` — a unique constraint on
   (initiative_id, version). Makes the version-increment race-safety pattern
   in questionnaire.py::_get_or_create_draft_assessment (IntegrityError
   catch-and-requery, mirroring the existing
   uq_assessment_one_draft_per_initiative CR-02 precedent) meaningful once
   `version` is actually computed as max(existing)+1 instead of always
   defaulting to 1 (D-15/HIST-01). Without this constraint, two concurrent
   "first answer of a new retake" requests could both compute the same next
   version number and both succeed, producing two Assessment rows sharing
   one version number.
2. `last_viewed_category_id` (nullable String) — persists the category the
   user was last VIEWING server-side (D-08), independent of which question
   they last answered, so a hard-refresh/new-tab resumes at the right page
   even if no answer was saved on that page yet.

Hand-written, not autogenerate, per this table's established migration
convention (i9d7e6f5a4b3).

Downgrade: reverses both changes in the opposite order they were applied
(drop the constraint, then drop the column) — not lossy, since neither
change altered or removed any existing data; `last_viewed_category_id` is a
new nullable column with no prior values to lose, and the unique constraint
only rejects future duplicate-version inserts, it does not alter any
existing row.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "j1a2b3c4d5e6"
down_revision = "i9d7e6f5a4b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment",
        sa.Column("last_viewed_category_id", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_assessment_version_per_initiative",
        "assessment",
        ["initiative_id", "version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_assessment_version_per_initiative", "assessment", type_="unique")
    op.drop_column("assessment", "last_viewed_category_id")
