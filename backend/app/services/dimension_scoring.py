"""Dimension-scoring service (SCOR-01/02/04).

Pure internal service — no FastAPI route lives here (D-03). Computes the
per-category equal-weight dimension scores (D-02: `Dimensiescore = Som van
alle antwoorden / aantal vragen binnen de dimensie`) and enforces the
server-side completion gate (D-06/D-07) that every score/report endpoint
must call before scoring.

All structure (category ids/names/question counts, full question-id set) is
derived at call time from the `dssc_questionnaire_config` dict passed in by
callers (surfaced via `Depends(get_dssc_questionnaire_config)`) — never
hardcoded, since the config's current question/category shape is an
explicit placeholder pending real content (QSTN-05).
"""

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.assessment import Assessment, AssessmentStatus
from app.models.questionnaire import QuestionnaireAnswer


def _full_question_ids(config: dict) -> set[str]:
    """Every question id across all config categories. Mirrors
    questionnaire.py's `valid_categories_by_question` config-comprehension
    idiom — config is the source of truth for structure, never a hardcoded
    count (RESEARCH "Don't Hand-Roll")."""
    return {q["id"] for cat in config["categories"] for q in cat["questions"]}


def _category_question_counts(config: dict) -> dict[str, int]:
    """Per-category question count, derived from config — never a shared
    constant across dimensions (SCOR-01 adjacency)."""
    return {cat["id"]: len(cat["questions"]) for cat in config["categories"]}


def _category_names(config: dict) -> dict[str, str]:
    """Per-category display name, derived from config."""
    return {cat["id"]: cat["name"] for cat in config["categories"]}


def get_current_assessment(session: Session, initiative_id: int) -> Assessment | None:
    """Most-recent draft Assessment for this initiative. Mirrors the exact
    lookup already used in questionnaire.py's `_get_or_create_draft_assessment`
    — D-06 explicitly anchors completion on "the assessment's current
    Assessment row", not on Assessment.status, and no submitted-assessment
    history exists yet (Phase 15's job), so "current" == "most recent draft"
    today. Does NOT reuse reports.py's `_get_answers_for_initiative` join,
    which sums across every assessment of an initiative — this scopes to a
    single current draft assessment only."""
    return session.exec(
        select(Assessment)
        .where(
            Assessment.initiative_id == initiative_id,
            Assessment.status == AssessmentStatus.draft,
        )
        .order_by(Assessment.created_at.desc())  # type: ignore[attr-defined]
    ).first()


def assert_assessment_complete(session: Session, initiative_id: int, config: dict) -> Assessment:
    """Raises HTTPException(422) if no draft assessment exists, or if the
    initiative's current draft assessment has not answered every question_id
    in the config (SCOR-04, D-06/D-07). Returns the Assessment on success so
    callers don't have to re-query it.

    Completeness is derived server-side from the DB's actual answered
    question_id rows for the current draft assessment, compared against the
    config's question-id set, on every call — never from a client-supplied
    flag or cached value (T-14-01). The same generic 422 detail is used for
    both the no-assessment and incomplete-assessment cases so the response
    never enumerates which question ids are missing (T-14-02)."""
    assessment = get_current_assessment(session, initiative_id)
    if assessment is None:
        raise HTTPException(status_code=422, detail="Questionnaire not fully answered")

    answered_ids = set(
        session.exec(
            select(QuestionnaireAnswer.question_id).where(
                QuestionnaireAnswer.assessment_id == assessment.id
            )
        ).all()
    )
    missing = _full_question_ids(config) - answered_ids
    if missing:
        raise HTTPException(status_code=422, detail="Questionnaire not fully answered")
    return assessment


def compute_dimension_scores(session: Session, assessment_id: int, config: dict) -> list[dict]:
    """SCOR-01/02: one entry per config category, in config category order,
    each `{category_id, name, score}` with score = round(sum(scores in that
    category) / that category's own config-derived question count, 2), a
    float in [1.0, 5.0]. No per-question or per-category weight multiplier
    appears anywhere in this computation.

    Caller MUST have already verified completeness via
    `assert_assessment_complete` (SCOR-04) — this function does not
    re-check and will silently divide by each category's config-derived
    question count regardless of how many rows actually exist."""
    rows = session.exec(
        select(
            QuestionnaireAnswer.category_id,
            func.sum(QuestionnaireAnswer.score),
        )
        .where(QuestionnaireAnswer.assessment_id == assessment_id)
        .group_by(QuestionnaireAnswer.category_id)
    ).all()
    sums = dict(rows)
    counts = _category_question_counts(config)
    names = _category_names(config)

    return [
        {
            "category_id": cat_id,
            "name": names[cat_id],
            "score": round(sums.get(cat_id, 0) / n_questions, 2),
        }
        for cat_id, n_questions in counts.items()
    ]
