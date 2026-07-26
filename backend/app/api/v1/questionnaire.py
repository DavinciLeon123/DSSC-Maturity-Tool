from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.assessment import Assessment, AssessmentStatus
from app.models.initiative import Initiative, InitiativeStatus
from app.models.questionnaire import QuestionnaireAnswer
from app.models.user import User
from app.schemas.questionnaire import AnswerCreate, AnswerRead, LastViewedCategoryUpdate

router = APIRouter(tags=["questionnaire"])


def get_user_or_ip_key(request: Request) -> str:
    """SAVE-03: per-authenticated-user rate-limit key, falling back to
    IP-keying only for unauthenticated/malformed requests.

    Pitfall 1: slowapi's key_func receives only the raw Request — FastAPI's
    Depends()-injected values (e.g. current_user) are not resolved yet at
    this point, so the JWT is decoded directly here via the existing
    decode_access_token (reused verbatim, not a second JWT parser).
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        sub = decode_access_token(auth_header[len("Bearer ") :])
        if sub:
            return f"user:{sub}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip_key)


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
    be verified by the caller before this is invoked.

    CR-02: two concurrent first-answer requests for the same initiative can
    both see "no draft exists" and race to insert. The partial unique index
    `uq_assessment_one_draft_per_initiative` (migration i9d7e6f5a4b3)
    guarantees only one insert wins at the DB level; the loser catches the
    resulting IntegrityError, rolls back its own failed insert, and
    re-queries for the winner's row rather than silently creating a second,
    orphaned draft Assessment.

    D-15/HIST-01: when no draft exists, the new draft's version is computed
    as max(existing versions for this initiative, across draft AND
    submitted rows) + 1 — never a hardcoded 1 — so a retake after a prior
    submission is a distinguishable, permanently preserved new version.
    Pitfall 4: two concurrent "first answer of a new retake" requests could
    race between this SELECT and the INSERT; the new
    uq_assessment_version_per_initiative unique constraint (migration
    j1a2b3c4d5e6) lets Postgres reject the loser's duplicate-version
    insert, and the existing IntegrityError-catch-and-requery below now
    also defends this constraint, not just the draft-uniqueness one.
    """
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

    max_version = session.exec(
        select(func.max(Assessment.version)).where(Assessment.initiative_id == initiative_id)
    ).one()
    next_version = (max_version or 0) + 1

    assessment = Assessment(initiative_id=initiative_id, version=next_version)
    session.add(assessment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        assessment = session.exec(
            select(Assessment)
            .where(
                Assessment.initiative_id == initiative_id,
                Assessment.status == AssessmentStatus.draft,
            )
            .order_by(Assessment.created_at.desc())  # type: ignore[attr-defined]
        ).first()
        if assessment is None:
            # The conflict wasn't actually a duplicate draft (e.g. a
            # different constraint violation) — surface the real error
            # rather than masking it.
            raise
        return assessment
    session.refresh(assessment)
    return assessment


@router.put(
    "/questionnaire/initiatives/{initiative_id}/answers/{question_id}", response_model=AnswerRead
)
@limiter.limit("120/minute")  # [ASSUMED — RESEARCH A1] per-user, up from 60/minute IP-keyed
def upsert_answer(
    request: Request,
    initiative_id: int,
    question_id: str,
    answer_in: AnswerCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
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

    # WR-03: the path param is the source of truth for question_id (used for
    # both the insert and the re-fetch below); reject a body that disagrees
    # rather than silently ignoring answer_in.question_id.
    if answer_in.question_id != question_id:
        raise HTTPException(
            status_code=422,
            detail="Body question_id does not match the URL path question_id",
        )

    # WR-02: validate question_id/category_id against the loaded DSSC config
    # before persisting — previously only score bounds were schema-checked,
    # so an unknown question_id or a category_id that doesn't match the
    # question's real category would be silently persisted, seeding bad data
    # future scoring/reporting (Phase 14/16) will key off.
    valid_categories_by_question = {
        q["id"]: q["category_id"]
        for cat in config.get("categories", [])
        for q in cat.get("questions", [])
    }
    if question_id not in valid_categories_by_question:
        raise HTTPException(status_code=422, detail="Unknown question_id")
    if valid_categories_by_question[question_id] != answer_in.category_id:
        raise HTTPException(
            status_code=422,
            detail="category_id does not match this question's category in the config",
        )

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


@router.get("/questionnaire/initiatives/{initiative_id}/last-viewed-category")
def get_last_viewed_category(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """D-08: read-side counterpart to the PATCH endpoint below, so the
    wizard can resume at the last-viewed category on initial mount
    (RESEARCH Open Question 1 / plan 15-04 Task 2).

    [Rule 3 auto-fix — plan 15-04]: plan 15-01 shipped only the write side
    of D-08 (the PATCH route). 15-04's mount flow needs to read this value
    back before the wizard renders its first category, and no route
    exposed it (`GET .../answers` returns only answer rows, `InitiativeRead`
    has no assessment fields). This is a minimal, additive read mirroring
    the PATCH route's own ownership checks — no new column/migration, no
    architectural change — so it is fixed inline rather than blocking the
    whole plan on a checkpoint.

    Re-derives ownership exactly like get_answers (security V4). Returns
    None (not a 404) when no draft assessment exists yet — a first-ever
    visit has nothing to resume, which is not an error condition."""
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
    return {"last_viewed_category_id": assessment.last_viewed_category_id if assessment else None}


@router.patch("/questionnaire/initiatives/{initiative_id}/last-viewed-category")
@limiter.limit("120/minute")
def update_last_viewed_category(
    request: Request,
    initiative_id: int,
    body: LastViewedCategoryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """D-08: persist the category the user is currently VIEWING, written
    UNCONDITIONALLY — no answer required. This is the single, exact resume
    write path: a user who navigates to a category and looks around without
    answering anything still resumes there on a hard refresh/new tab,
    rather than being sent back to wherever they last saved an answer
    (RESEARCH Open Question 1). Deliberately not piggybacked onto
    upsert_answer — that path stays unchanged for last-viewed purposes.

    Re-derives ownership exactly like get_answers (security V4).

    Rule 2 auto-fix (not explicit in the plan text): guarded by the same
    CR-01 submitted-lock as upsert_answer. Without this, _get_or_create_
    draft_assessment would silently start a brand-new (incremented-version)
    draft as a side effect of merely viewing a page after submission —
    bypassing D-13's requirement that a retake only ever starts via an
    explicit "Start new assessment" action.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")
    if initiative.status == InitiativeStatus.submitted:
        raise HTTPException(status_code=403, detail="Submitted assessments cannot be edited")

    assessment = _get_or_create_draft_assessment(session, initiative_id)
    assessment.last_viewed_category_id = body.category_id
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return {"last_viewed_category_id": assessment.last_viewed_category_id}
