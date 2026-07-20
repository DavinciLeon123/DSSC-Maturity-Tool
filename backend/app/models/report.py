from datetime import datetime

from sqlalchemy import Text
from sqlmodel import Column, Field, SQLModel


class ComplianceReport(SQLModel, table=True):
    __tablename__ = "compliance_report"

    id: int | None = Field(default=None, primary_key=True)
    initiative_id: int = Field(foreign_key="initiative.id", index=True, unique=True)
    html_content: str = Field(sa_column=Column(Text))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    questionnaire_version: str
    total_answers: int
    critical_count: int
    non_critical_count: int
    compliant_count: int
