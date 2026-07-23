"""Plain fixture-factory functions (NOT factory_boy — per D-03/RESEARCH.md
Alternatives Considered) producing synthetic, production-shaped fixture data
using `faker` for realistic emails/org names.

These are plain callables, not pytest fixtures themselves — call them from a
test (or a thin pytest fixture wrapper in the consuming test file) passing a
`session` so the caller controls commit timing and can build multi-row
graphs (e.g. an initiative with several answers) in one transaction.
"""

import uuid

from faker import Faker
from sqlmodel import Session

from app.core.security import hash_password
from app.models.initiative import SECTOR_OPTIONS, Initiative, InitiativeStatus, ParticipantType
from app.models.questionnaire import AnswerValue, QuestionnaireAnswer
from app.models.report import ComplianceReport
from app.models.user import User

fake = Faker()


def make_user(
    session: Session,
    *,
    role: str = "USER",
    participant_type: str = "DSI",
    password: str = "Str0ngPassw0rd!123",
    email: str | None = None,
) -> User:
    """Build a loginable User — password is hashed via hash_password so
    verify_password(password, user.hashed_password) succeeds (a raw-string
    password would silently make every login test fail)."""
    user = User(
        email=email or f"{uuid.uuid4().hex[:10]}-{fake.user_name()}@{fake.free_email_domain()}",
        hashed_password=hash_password(password),
        role=role,
        participant_type=participant_type,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_initiative(
    session: Session,
    *,
    user: User,
    status: InitiativeStatus = InitiativeStatus.draft,
    sector: str | None = None,
    participant_type: ParticipantType | None = None,
) -> Initiative:
    """Build an Initiative for `user`. Respects the one-initiative-per-user
    unique constraint on Initiative.user_id — callers must not call this
    twice for the same user."""
    initiative = Initiative(
        user_id=user.id,
        name=fake.company(),
        description=fake.catch_phrase(),
        sector=sector or fake.random_element(SECTOR_OPTIONS),
        organization=fake.company(),
        contact_name=fake.name(),
        contact_email=fake.company_email(),
        participant_type=participant_type
        or (ParticipantType.dsi if user.participant_type == "DSI" else ParticipantType.sp),
        status=status,
    )
    session.add(initiative)
    session.commit()
    session.refresh(initiative)
    return initiative


def make_submitted_initiative(session: Session, *, user: User, **kwargs) -> Initiative:
    """Convenience wrapper: a `submitted`-status Initiative, needed by
    admin/heatmap tests that filter on submission status."""
    return make_initiative(session, user=user, status=InitiativeStatus.submitted, **kwargs)


def make_answer(
    session: Session,
    *,
    initiative: Initiative,
    question_id: str | None = None,
    mami_code: str | None = None,
    answer_value: AnswerValue = AnswerValue.yes,
    questionnaire_version: str = "2.0",
) -> QuestionnaireAnswer:
    """Build a QuestionnaireAnswer using the AnswerValue enum member (not a
    raw string) — this exact enum is what Phase 13 changes, so factories
    must fail loudly (ValueError/TypeError) rather than silently accept a
    string if the enum shape changes. Respects the unique
    (initiative_id, question_id) constraint — pass a distinct question_id
    per call for the same initiative."""
    qid = question_id or f"q_{uuid.uuid4().hex[:8]}"
    answer = QuestionnaireAnswer(
        initiative_id=initiative.id,
        question_id=qid,
        mami_code=mami_code or f"S-HRA-{fake.random_int(1, 4)}.{fake.random_int(1, 2)}",
        questionnaire_version=questionnaire_version,
        answer_value=answer_value,
    )
    session.add(answer)
    session.commit()
    session.refresh(answer)
    return answer


def make_report(
    session: Session,
    *,
    initiative: Initiative,
    html_content: str | None = None,
    total_answers: int = 27,
    critical_count: int = 2,
    non_critical_count: int = 3,
    compliant_count: int = 22,
    questionnaire_version: str = "2.0",
) -> ComplianceReport:
    """ComplianceReport.initiative_id is unique=True — matches the real
    pg_insert().on_conflict_do_update(index_elements=["initiative_id"])
    upsert reports.py relies on (RESEARCH.md Pitfall 5); factory-created
    rows exercise the same constraint the real upsert depends on."""
    report = ComplianceReport(
        initiative_id=initiative.id,
        html_content=html_content or f"<html><body>{fake.paragraph()}</body></html>",
        questionnaire_version=questionnaire_version,
        total_answers=total_answers,
        critical_count=critical_count,
        non_critical_count=non_critical_count,
        compliant_count=compliant_count,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
