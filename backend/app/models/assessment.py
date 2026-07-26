"""Assessment entity — the new join point between an Initiative and its
questionnaire answers (D-06/D-07).

An Assessment row is created lazily (status=draft) on the FIRST answer write
for an initiative, not deferred to submission — this gives Phase 15's
autosave/retake requirements (SAVE-01..04, HIST-01/02) a stable row to write
against from question 1, without Phase 13 implementing that behavior itself.
`version`/`created_at`/`submitted_at` together satisfy Phase 15's "dated
version" need without a redundant field (RESEARCH Open Question 1).

Phase 15 (this plan) adds three things:
- `last_viewed_category_id` (D-08): persists the category the user was last
  VIEWING (not merely last-answered), written unconditionally by a dedicated
  PATCH endpoint so a hard-refresh resumes at the right page even if the
  user navigated to a category without answering anything there yet.
- `uq_assessment_version_per_initiative` (D-15/HIST-01, Pitfall 4): a
  DB-level uniqueness guarantee on (initiative_id, version) that makes the
  IntegrityError-catch-and-requery race-safety pattern in
  `_get_or_create_draft_assessment` meaningful once `version` is actually
  computed instead of always defaulting to 1. Declared here on the model
  (not just in the migration) so `SQLModel.metadata.create_all()`-built test
  databases enforce it too — the migration in
  `j1a2b3c4d5e6_assessment_version_lastviewed.py` applies the same
  constraint to real Postgres via Alembic.
- `dimension_scores` (HIST-02, gap-closure plan 15-07): a nullable JSONB
  snapshot of the per-dimension scores computed by
  `compute_dimension_scores` at the moment `submit_initiative` flips this
  row to `submitted`. Freezing the snapshot here — rather than always
  recomputing from the live questionnaire config — is what makes a
  submitted assessment's displayed history immutable: once the config
  changes (it is explicitly a placeholder pending real QSTN-05 content),
  every already-submitted version's history must still show what the user
  actually answered against, not the new config. `list_assessment_history`
  prefers this snapshot when present, falling back to a live recompute only
  for legacy submitted rows that predate this column.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AssessmentStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"


class Assessment(SQLModel, table=True):
    __tablename__ = "assessment"
    __table_args__ = (
        UniqueConstraint("initiative_id", "version", name="uq_assessment_version_per_initiative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    version: int = Field(default=1)
    status: AssessmentStatus = Field(default=AssessmentStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None
    last_viewed_category_id: str | None = Field(default=None)
    dimension_scores: list[dict] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
