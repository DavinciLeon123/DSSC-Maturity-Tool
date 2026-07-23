"""Assessment entity — the new join point between an Initiative and its
questionnaire answers (D-06/D-07).

An Assessment row is created lazily (status=draft) on the FIRST answer write
for an initiative, not deferred to submission — this gives Phase 15's
autosave/retake requirements (SAVE-01..04, HIST-01/02) a stable row to write
against from question 1, without Phase 13 implementing that behavior itself.
`version`/`created_at`/`submitted_at` together satisfy Phase 15's "dated
version" need without a redundant field (RESEARCH Open Question 1).
"""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class AssessmentStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"


class Assessment(SQLModel, table=True):
    __tablename__ = "assessment"

    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    version: int = Field(default=1)
    status: AssessmentStatus = Field(default=AssessmentStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None
