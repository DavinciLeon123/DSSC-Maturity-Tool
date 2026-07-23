from datetime import datetime

from pydantic import BaseModel, Field


class AnswerCreate(BaseModel):
    question_id: str
    category_id: str
    score: int = Field(ge=1, le=5)  # security V5 — reject out-of-range scores at the schema layer


class AnswerRead(BaseModel):
    id: int
    assessment_id: int
    question_id: str
    category_id: str
    score: int
    answered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
