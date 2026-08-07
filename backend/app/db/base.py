from sqlmodel import SQLModel  # noqa: F401

from app.models.assessment import Assessment  # noqa: F401
from app.models.initiative import Initiative  # noqa: F401
from app.models.questionnaire import QuestionnaireAnswer  # noqa: F401
from app.models.questionnaire_answer_archive import QuestionnaireAnswerV1Archive  # noqa: F401
from app.models.report import ComplianceReport  # noqa: F401

# DO NOT REMOVE — Alembic needs these imports to autogenerate migrations
from app.models.user import User  # noqa: F401
