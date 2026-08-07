from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class QuestionnaireAnswer(SQLModel, table=True):
    """New-schema (v2) answer shape (D-02): keyed by `assessment_id`, not
    `initiative_id` — every answer belongs to an `Assessment` (D-06). Carries
    the new config's `category_id` and an integer 1-5 `score`, replacing the
    old `mami_code`/`answer_value` 3-way-enum shape entirely. The OLD shape
    lives on, read-only, in `QuestionnaireAnswerV1Archive`
    (questionnaire_answer_archive.py) — this table does not need to carry
    legacy enum columns going forward.
    """

    __tablename__ = "questionnaire_answer"
    __table_args__ = (
        UniqueConstraint("assessment_id", "question_id", name="uq_answer_per_question_v2"),
    )

    id: int | None = Field(default=None, primary_key=True)
    assessment_id: int = Field(foreign_key="assessment.id", index=True)
    question_id: str = Field(index=True)  # e.g. "q-1-1" (new dssc-questionnaire.json id)
    category_id: str = Field(index=True)  # e.g. "cat-1" (new config category id)
    score: int = Field(ge=1, le=5)  # security V5 — DB-level CHECK added in the 13-04 migration
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
