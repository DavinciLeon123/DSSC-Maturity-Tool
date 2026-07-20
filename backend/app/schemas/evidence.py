from pydantic import BaseModel
from datetime import datetime


class EvidenceCreate(BaseModel):
    question_id: str
    mami_code: str
    url: str


class EvidenceRead(BaseModel):
    id: int
    initiative_id: int
    question_id: str
    mami_code: str
    url: str
    created_at: datetime

    class Config:
        from_attributes = True
