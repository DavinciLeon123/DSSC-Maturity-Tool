from datetime import datetime
from enum import Enum

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AnswerValue(str, Enum):
    yes = "YES"
    not_there_yet = "NOT_THERE_YET"
    not_applicable = "NOT_APPLICABLE"


class QuestionnaireAnswer(SQLModel, table=True):
    __tablename__ = "questionnaire_answer"
    __table_args__ = (
        UniqueConstraint("initiative_id", "question_id", name="uq_answer_per_question"),
    )

    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    question_id: str = Field(index=True)  # e.g. "q_DSI-S-HRA-1.1"
    mami_code: str = Field(index=True)  # e.g. "S-HRA-1.1" (denormalized)
    questionnaire_version: str  # e.g. "2.0"
    answer_value: AnswerValue
    followup_selections: list[str] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )  # Multi-select follow-up choices
    followup_other: str | None = None  # Free-text "Other" follow-up input
    rationale: str | None = None  # DEPRECATED — kept for data migration
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
