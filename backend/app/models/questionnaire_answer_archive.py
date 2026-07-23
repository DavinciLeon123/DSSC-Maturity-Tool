"""Read-only mirror of the pre-migration (v1.0 MAMI) questionnaire_answer
shape (D-01/MIGR-01).

This table is populated once by the 13-04 Alembic migration (archive-table
split — copy-then-reshape, RESEARCH Pattern 2) and is not written to by any
endpoint this phase (D-04: DB-level queryable access only). It is defined
here as a real SQLModel table (not just a raw Alembic table) so it stays
importable/queryable and is registered for Alembic autogenerate consistency
(RESEARCH Open Question 2).

Deliberately has NO foreign key to `initiative.id` — archived rows must
survive an admin hard-delete of a legacy initiative (RESEARCH Anti-Pattern /
Assumption A2; MIGR-01 preservation is the whole point of this table).

`answer_value` is declared with an explicit `sa.String` column (NOT a bare
`(str, Enum)` annotation) so this model's shape matches what the 13-04
migration writes with `sa.String()`, keeping `SQLModel.metadata.create_all()`
-built test schema and migration-built production schema from diverging into
a native Postgres ENUM (RESEARCH Pitfall 1).
"""

from datetime import datetime

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class QuestionnaireAnswerV1Archive(SQLModel, table=True):
    __tablename__ = "questionnaire_answer_v1_archive"

    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(index=True)  # deliberately NO FK — see module docstring (A2)
    question_id: str = Field(index=True)
    mami_code: str = Field(index=True)
    questionnaire_version: str
    answer_value: str = Field(sa_column=Column(String, nullable=False))  # NOT AnswerValue enum
    followup_selections: list[str] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    followup_other: str | None = None
    rationale: str | None = None
    answered_at: datetime
    updated_at: datetime
