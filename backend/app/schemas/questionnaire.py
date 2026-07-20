from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.questionnaire import AnswerValue


class AnswerCreate(BaseModel):
    question_id: str
    mami_code: str
    questionnaire_version: str
    answer_value: AnswerValue
    followup_selections: Optional[List[str]] = None
    followup_other: Optional[str] = None


class AnswerRead(BaseModel):
    id: int
    initiative_id: int
    question_id: str
    mami_code: str
    questionnaire_version: str
    answer_value: AnswerValue
    followup_selections: Optional[List[str]]
    followup_other: Optional[str]
    answered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
