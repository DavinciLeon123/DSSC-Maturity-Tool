from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.v1.questionnaire import _get_or_create_draft_assessment
from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.assessment import Assessment, AssessmentStatus
from app.models.initiative import Initiative, InitiativeStatus
from app.models.user import User
from app.schemas.assessment import AssessmentSummary
from app.schemas.initiative import InitiativeCreate, InitiativeRead, InitiativeUpdate
from app.services.dimension_scoring import compute_dimension_scores, list_submitted_assessments

router = APIRouter(prefix="/initiatives", tags=["initiatives"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InitiativeRead)
def create_initiative(
    initiative_in: InitiativeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(Initiative).where(Initiative.user_id == current_user.id)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a registered initiative. Only one per user is allowed.",
        )
    initiative = Initiative(
        user_id=current_user.id,
        participant_type=current_user.participant_type,
        **initiative_in.model_dump(),
    )
    session.add(initiative)
    session.commit()
    session.refresh(initiative)
    return _to_read(initiative)


@router.get("/me", response_model=InitiativeRead)
def get_my_initiative(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    initiative = session.exec(
        select(Initiative).where(Initiative.user_id == current_user.id)
    ).first()
    if not initiative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No initiative found")
    return _to_read(initiative)


@router.patch("/{initiative_id}", response_model=InitiativeRead)
def update_initiative(
    initiative_id: int,
    update_in: InitiativeUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your initiative")
    if initiative.status == InitiativeStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Submitted initiatives cannot be edited",
        )
    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(initiative, field, value)
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)
    session.commit()
    session.refresh(initiative)
    return _to_read(initiative)


@router.post("/{initiative_id}/submit", status_code=200)
def submit_initiative(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Mark initiative as submitted. Idempotent — re-submitting an already-submitted one is OK.

    CR-01: also flips the initiative's current draft Assessment (if any) to
    submitted and stamps submitted_at — this is what actually locks
    questionnaire answers against further edits (enforced in
    questionnaire.py's upsert_answer), not just the Initiative row.

    HIST-02 (gap-closure plan 15-07): also computes and freezes the
    per-dimension score snapshot on `assessment.dimension_scores`, against
    the config AS IT EXISTS RIGHT NOW (submission time). This is the one
    and only place scores are computed for a submitted assessment — later
    edits to the live config must never retroactively change what this
    already-submitted version displays in history.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")
    initiative.status = InitiativeStatus.submitted
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)

    assessment = session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if assessment:
        assessment.status = AssessmentStatus.submitted
        assessment.submitted_at = datetime.utcnow()
        assert assessment.id is not None  # already persisted (draft rows are lazily created)
        assessment.dimension_scores = compute_dimension_scores(session, assessment.id, config)
        session.add(assessment)

    session.commit()
    return {"message": "Initiative submitted successfully", "status": initiative.status.value}


@router.post("/{initiative_id}/retake", status_code=status.HTTP_201_CREATED)
def retake_initiative(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """HIST-01 gap closure (CR-01): the explicit, confirmed user action that
    actually unlocks a submitted initiative for a retake and creates a fresh,
    version-incremented draft Assessment — the missing reset that made the
    version-increment machinery in _get_or_create_draft_assessment
    unreachable through the real UI (15-VERIFICATION.md Gap 1).

    Ownership is re-derived here exactly like every other route in this file
    (Initiative.user_id == current_user.id, 404/403) before any state change
    — the path id is never trusted as authorization on its own (security V4,
    T-15-06-01).

    Only a currently-submitted initiative can be retaken (409 otherwise) —
    this enforces D-13 (a retake is an explicit action on a completed
    assessment, never an implicit side effect) and prevents silently
    version-bumping a draft that is still in progress (T-15-06-03).
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")
    if initiative.status != InitiativeStatus.submitted:
        raise HTTPException(status_code=409, detail="Only a submitted initiative can be retaken")

    initiative.status = InitiativeStatus.draft
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)

    # Reuse the canonical, race-safe version-increment path (T-15-06-02):
    # this commits the initiative.status reset above and the new draft
    # Assessment atomically in the same session/transaction.
    assessment = _get_or_create_draft_assessment(session, initiative_id)

    return {
        "message": "New assessment started",
        "version": assessment.version,
        "assessment_id": assessment.id,
    }


@router.get("/{initiative_id}/assessments", response_model=list[AssessmentSummary])
def list_assessment_history(
    initiative_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """HIST-02: owner-scoped, version-ordered list of an initiative's
    SUBMITTED assessment versions with per-dimension scores (D-16a/D-16b
    data source).

    Ownership is re-derived here exactly like every other route in this
    file (Initiative.user_id == current_user.id, 404/403) before any
    assessment data is returned (security T-15-04). Deliberately calls
    `list_submitted_assessments` (never `get_current_assessment`, which is
    draft-only per RESEARCH Pitfall 5) so an in-progress retake never
    leaks into the history list.
    """
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    submitted = list_submitted_assessments(session, initiative_id)
    return [_to_summary(a, session, config) for a in submitted]


def _to_summary(a: Assessment, session: Session, config: dict) -> AssessmentSummary:
    """HIST-02 (gap-closure plan 15-07): prefer the frozen `dimension_scores`
    snapshot written at submit time — only fall back to a live recompute for
    legacy submitted rows that predate the snapshot column (dimension_scores
    is None). This is what makes history immutable under later config
    drift: once a version carries a snapshot, this function never touches
    the live config for it again."""
    assert a.id is not None  # always called on a persisted assessment
    scores = (
        a.dimension_scores
        if a.dimension_scores is not None
        else compute_dimension_scores(session, a.id, config)
    )
    overall_average = round(sum(d["score"] for d in scores) / len(scores), 2) if scores else 0.0
    return AssessmentSummary(
        id=a.id,
        version=a.version,
        submitted_at=a.submitted_at.isoformat() if a.submitted_at else "",
        overall_average=overall_average,
        dimension_scores=scores,
    )


def _to_read(i: Initiative) -> InitiativeRead:
    assert i.id is not None  # always called on a persisted initiative
    return InitiativeRead(
        id=i.id,
        user_id=i.user_id,
        name=i.name,
        description=i.description,
        sector=i.sector,
        sector_other=i.sector_other,
        contact_name=i.contact_name,
        contact_email=i.contact_email,
        organization=i.organization,
        # D-12/Pitfall 5: participant_type is nullable now — guard .value so a
        # future None (legacy-tagged or new-record) doesn't AttributeError.
        participant_type=i.participant_type.value if i.participant_type else None,
        status=i.status.value,
        created_at=i.created_at.isoformat(),
        updated_at=i.updated_at.isoformat(),
    )
