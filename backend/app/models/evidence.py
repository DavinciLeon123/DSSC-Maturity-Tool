from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class EvidenceURL(SQLModel, table=True):
    __tablename__ = "evidence_url"

    id: Optional[int] = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True)
    question_id: str = Field(index=True)
    mami_code: str = Field(index=True)
    url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
