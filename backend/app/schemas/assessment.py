"""Pydantic schema for the read-side of retake history (HIST-02).

Mirrors AnswerRead's plain-BaseModel convention (backend/app/schemas/
questionnaire.py) — no `from_attributes`/ORM config needed since
AssessmentSummary is assembled by hand in the route (initiatives.py's
`_to_summary`), not returned directly from an ORM instance.
"""

from pydantic import BaseModel


class AssessmentSummary(BaseModel):
    id: int
    version: int
    submitted_at: str
    overall_average: float
    dimension_scores: list[dict]
