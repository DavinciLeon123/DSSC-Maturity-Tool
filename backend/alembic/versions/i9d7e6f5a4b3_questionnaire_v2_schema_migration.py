"""Questionnaire v2 schema migration: Assessment entity, archive-table split,
questionnaire_answer reshape (MIGR-01, D-01/D-02/D-03/D-06)

Revision ID: i9d7e6f5a4b3
Revises: h8c6d5e4f3a2
Create Date: 2026-07-23

This is the phase's core data migration (13-04). It implements the
archive-table-split pattern (RESEARCH Pattern 2) rather than an in-place
column remap, because the answer *shape* itself changes (3-way categorical
enum -> 1-5 integer score), not just its values — the existing
f6a4b3c2d1e9 precedent (same-table value remap) does not apply here.

Changes (in order):
1. Create the new `assessment` table (Assessment entity, D-06/D-07) — the
   new join point between `initiative` and `questionnaire_answer`.
2. Create `questionnaire_answer_v1_archive`, mirroring the OLD
   questionnaire_answer column shape verbatim (`answer_value` as explicit
   sa.String(), never a native Postgres ENUM — RESEARCH Pitfall 1).
   Deliberately has NO foreign key to `initiative.id` so archived rows
   survive a later admin hard-delete of a legacy initiative (D-01/A2).
3. Copy every existing questionnaire_answer row into the archive verbatim
   (MIGR-01 — never delete compliance-relevant data).
4. Add `initiative.schema_version` (server_default 'v2', D-03) and tag
   initiatives that have archived answers as 'v1_legacy'.
5. Make `initiative.participant_type` / `user.participant_type` nullable
   (D-12) — kept for historical reference, never populated going forward.
6. Drop the old-shape `questionnaire_answer` and recreate it with the new
   assessment_id/category_id/score shape (D-02), including a DB-level
   CHECK (score BETWEEN 1 AND 5) for defense-in-depth (security V5).

Does NOT touch `compliance_report` or `evidence_url` (D-05 / RESEARCH
Pitfall 4; evidence_url plumbing was already removed at the application
layer in 13-02 — this migration does not need to drop that table either,
since it carries no FK/shape coupling to anything changed here and dropping
tables outside this migration's stated scope risks silently deleting data
a future phase didn't ask for).

Downgrade lossiness: reconstructing the old-shape questionnaire_answer from
the archive table is lossy for any NEW-shape (assessment_id/category_id/
score) answers written after the original upgrade — those have no
old-shape representation and are not restored. This is the same accepted
lossiness precedent as f6a4b3c2d1e9's downgrade (which also cannot
distinguish original NO vs. COMPLY_EXPLAIN once merged).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "i9d7e6f5a4b3"
down_revision = "h8c6d5e4f3a2"
branch_labels = None
depends_on = None

_ARCHIVE_COLUMNS = (
    "id, initiative_id, question_id, mami_code, questionnaire_version, "
    "answer_value, followup_selections, followup_other, rationale, "
    "answered_at, updated_at"
)


def upgrade() -> None:
    # 1. New Assessment entity (D-06/D-07) — the join point future answers key off.
    op.create_table(
        "assessment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiative.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_initiative_id"), "assessment", ["initiative_id"])
    # CR-02: guard against the lazy-create race in
    # questionnaire.py::_get_or_create_draft_assessment — two concurrent
    # first-answer requests for the same initiative could otherwise both see
    # "no draft exists" and each insert their own Assessment row, silently
    # orphaning any answers written against the older draft. A partial
    # unique index lets Postgres itself reject the second concurrent insert;
    # the application layer catches the resulting IntegrityError and
    # re-queries for the winning row instead of relying on an unguarded
    # check-then-insert.
    op.create_index(
        "uq_assessment_one_draft_per_initiative",
        "assessment",
        ["initiative_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    # 2. Archive table — mirrors the OLD questionnaire_answer shape verbatim.
    #    answer_value is sa.String(), NOT sa.Enum — RESEARCH Pitfall 1.
    #    Deliberately NO FK to initiative.id — must survive an admin
    #    hard-delete of a legacy initiative (D-01/A2).
    op.create_table(
        "questionnaire_answer_v1_archive",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("answer_value", sa.String(), nullable=False),
        sa.Column("followup_selections", JSONB, nullable=True),
        sa.Column("followup_other", sa.Text(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_questionnaire_answer_v1_archive_initiative_id"),
        "questionnaire_answer_v1_archive",
        ["initiative_id"],
    )
    op.create_index(
        op.f("ix_questionnaire_answer_v1_archive_question_id"),
        "questionnaire_answer_v1_archive",
        ["question_id"],
    )
    op.create_index(
        op.f("ix_questionnaire_answer_v1_archive_mami_code"),
        "questionnaire_answer_v1_archive",
        ["mami_code"],
    )

    # 3. Copy every existing row verbatim (MIGR-01 — never delete compliance-relevant data).
    op.execute(f"""
        INSERT INTO questionnaire_answer_v1_archive ({_ARCHIVE_COLUMNS})
        SELECT {_ARCHIVE_COLUMNS}
        FROM questionnaire_answer
    """)

    # 4. Tag initiatives that have archived answers as legacy (D-03), BEFORE
    #    the old questionnaire_answer table is dropped below.
    op.add_column(
        "initiative",
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v2"),
    )
    op.execute("""
        UPDATE initiative SET schema_version = 'v1_legacy'
        WHERE id IN (SELECT DISTINCT initiative_id FROM questionnaire_answer_v1_archive)
    """)
    # Real edge (RESEARCH Assumption Log / plan must_haves): an initiative
    # with ZERO prior answers produces zero archive rows and is correctly
    # left at the 'v2' default — it is indistinguishable from a brand new
    # initiative and needs no legacy handling.

    # 5. participant_type stays but stops being enforced going forward (D-12).
    op.alter_column("initiative", "participant_type", nullable=True)
    op.alter_column("user", "participant_type", nullable=True)

    # 6. Drop and recreate questionnaire_answer with the new 1-5-score shape.
    op.drop_table("questionnaire_answer")
    op.create_table(
        "questionnaire_answer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "question_id", name="uq_answer_per_question_v2"),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="ck_answer_score_range"),
    )
    op.create_index(
        op.f("ix_questionnaire_answer_assessment_id"), "questionnaire_answer", ["assessment_id"]
    )
    op.create_index(
        op.f("ix_questionnaire_answer_question_id"), "questionnaire_answer", ["question_id"]
    )
    op.create_index(
        op.f("ix_questionnaire_answer_category_id"), "questionnaire_answer", ["category_id"]
    )


def downgrade() -> None:
    # Reverse of step 5 — fill NULLs before re-enforcing NOT NULL, same
    # lossy-safe pattern as h8c6d5e4f3a2's downgrade.
    op.execute("UPDATE initiative SET participant_type = 'DSI' WHERE participant_type IS NULL")
    op.execute('UPDATE "user" SET participant_type = \'DSI\' WHERE participant_type IS NULL')
    op.alter_column("initiative", "participant_type", nullable=False)
    op.alter_column("user", "participant_type", nullable=False)

    # Reverse of step 4.
    op.drop_column("initiative", "schema_version")

    # Reverse of step 6 — drop the new-shape table first (FKs assessment.id,
    # must go before assessment itself is dropped below).
    op.drop_table("questionnaire_answer")

    # Reverse of step 2/3/6 — recreate the OLD-shape questionnaire_answer
    # table and restore archived rows into it.
    op.create_table(
        "questionnaire_answer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("mami_code", sa.String(), nullable=False),
        sa.Column("questionnaire_version", sa.String(), nullable=False),
        sa.Column("answer_value", sa.String(), nullable=False),
        sa.Column("followup_selections", JSONB, nullable=True),
        sa.Column("followup_other", sa.Text(), nullable=True),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiative.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("initiative_id", "question_id", name="uq_answer_per_question"),
    )
    op.create_index(
        op.f("ix_questionnaire_answer_initiative_id"), "questionnaire_answer", ["initiative_id"]
    )
    op.create_index(
        op.f("ix_questionnaire_answer_question_id"), "questionnaire_answer", ["question_id"]
    )
    op.create_index(
        op.f("ix_questionnaire_answer_mami_code"), "questionnaire_answer", ["mami_code"]
    )
    # LOSSY: any NEW-shape answers written after the original upgrade have no
    # old-shape representation and are NOT restored here — same accepted
    # lossiness precedent as f6a4b3c2d1e9's downgrade.
    op.execute(f"""
        INSERT INTO questionnaire_answer ({_ARCHIVE_COLUMNS})
        SELECT {_ARCHIVE_COLUMNS}
        FROM questionnaire_answer_v1_archive
    """)

    # Reverse of step 2.
    op.drop_table("questionnaire_answer_v1_archive")

    # Reverse of step 1 — safe now, nothing references assessment anymore.
    op.drop_table("assessment")
