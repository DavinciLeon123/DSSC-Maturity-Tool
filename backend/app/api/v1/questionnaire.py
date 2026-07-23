from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.assessment import Assessment, AssessmentStatus
from app.models.initiative import Initiative, InitiativeStatus
from app.models.questionnaire import QuestionnaireAnswer
from app.models.user import User
from app.schemas.questionnaire import AnswerCreate, AnswerRead

router = APIRouter(tags=["questionnaire"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/questionnaire/config")
def get_questionnaire_config_endpoint(
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Return the universal DSSC questionnaire config (52 questions / 6
    categories). Identical for every authenticated caller regardless of
    participant_type or whether they own an Initiative (D-10, QSTN-04).

    Per plan 13-01 assumption A1: the old participant_type-driven
    404-if-no-Initiative gate is dropped here — it was incidental coupling
    to the now-removed DSI/SP config selection, not load-bearing UX. This
    phase does not re-add an initiative-existence guard; if gating
    questionnaire access before registration is later desired, that is a
    separate ask for a future phase.
    """
    return config


def _get_or_create_draft_assessment(session: Session, initiative_id: int) -> Assessment:
    """Look up the initiative's current draft Assessment, or create one
    (D-06/D-07: an Assessment is created lazily on the first answer write,
    not deferred to submission). Ownership of `initiative_id` must already
    be verified by the caller before this is invoked."""
    assessment = session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if assessment:
        return assessment

    assessment = Assessment(initiative_id=initiative_id)
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


@router.put(
    "/questionnaire/initiatives/{initiative_id}/answers/{question_id}", response_model=AnswerRead
)
@limiter.limit("60/minute")
def upsert_answer(
    request: Request,
    initiative_id: int,
    question_id: str,
    answer_in: AnswerCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Upsert one answer for a question against the initiative's current
    draft Assessment. Creates the Assessment lazily on the first answer
    (D-06/D-07) and creates/updates the answer on subsequent saves.

    Enforces ownership: current user must own the initiative — re-derived
    through Assessment.initiative_id back to Initiative.user_id (security
    V4); assessment_id itself is never trusted as sufficient authorization
    on its own."""
    # Verify initiative ownership
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")
    # CR-01: submission is supposed to lock the questionnaire — mirror the
    # same immutability guarantee update_initiative already enforces for
    # initiative metadata (initiatives.py:update_initiative), otherwise
    # submit_initiative flipping Assessment.status is meaningless.
    if initiative.status == InitiativeStatus.submitted:
        raise HTTPException(status_code=403, detail="Submitted assessments cannot be edited")

    assessment = _get_or_create_draft_assessment(session, initiative_id)

    # PostgreSQL upsert (insert or update on conflict), keyed by the new
    # (assessment_id, question_id) constraint (D-06, RESEARCH Pattern 2).
    stmt = pg_insert(QuestionnaireAnswer).values(
        assessment_id=assessment.id,
        question_id=question_id,
        category_id=answer_in.category_id,
        score=answer_in.score,
        answered_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_answer_per_question_v2",
        set_={
            "category_id": stmt.excluded.category_id,
            "score": stmt.excluded.score,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.exec(stmt)
    session.commit()

    # Fetch and return the upserted row
    result = session.exec(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.assessment_id == assessment.id,
            QuestionnaireAnswer.question_id == question_id,
        )
    ).one()
    return result


@router.get("/questionnaire/initiatives/{initiative_id}/answers", response_model=list[AnswerRead])
def get_answers(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return all saved answers for the initiative's current draft
    Assessment (for save/resume — QUES-02). Re-derives ownership the same
    way as the upsert endpoint (security V4)."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    assessment = session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if not assessment:
        return []

    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.assessment_id == assessment.id)
    ).all()
    return answers
