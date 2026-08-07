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


class LastViewedCategoryUpdate(BaseModel):
    """D-08: request body for the dedicated PATCH .../last-viewed-category
    endpoint. Written unconditionally (independent of any answer save) so a
    bare navigation to a category still persists resume position."""

    category_id: str
