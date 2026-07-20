from pydantic import BaseModel
from datetime import datetime


class ReportRead(BaseModel):
    id: int
    initiative_id: int
    generated_at: datetime
    questionnaire_version: str
    total_answers: int
    critical_count: int
    non_critical_count: int
    compliant_count: int
