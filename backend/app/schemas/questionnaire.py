from datetime import datetime

from pydantic import BaseModel

from app.models.questionnaire import AnswerValue


class AnswerCreate(BaseModel):
    question_id: str
    mami_code: str
    questionnaire_version: str
    answer_value: AnswerValue
    followup_selections: list[str] | None = None
    followup_other: str | None = None


class AnswerRead(BaseModel):
    id: int
    initiative_id: int
    question_id: str
    mami_code: str
    questionnaire_version: str
    answer_value: AnswerValue
    followup_selections: list[str] | None
    followup_other: str | None
    answered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
