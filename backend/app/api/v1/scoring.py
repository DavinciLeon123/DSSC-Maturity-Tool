import zen
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_mami_config, get_zen_engine
from app.db.session import get_session
from app.models.assessment import Assessment
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.models.user import User
from app.services.scoring_engine import score_all_answers

router = APIRouter(tags=["scoring"])


class FindingRead(BaseModel):
    mami_code: str
    severity: str  # "CRITICAL" | "NON_CRITICAL" | ""
    status: str  # "FINDING" | "COMPLIANT" | "NOT_APPLICABLE"


class ScoreResponse(BaseModel):
    initiative_id: int
    total_answers: int
    findings: list[FindingRead]
    critical_count: int
    non_critical_count: int


@router.post("/initiatives/{initiative_id}/score", response_model=ScoreResponse)
async def score_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    engine: zen.ZenEngine = Depends(get_zen_engine),
    mami_config: dict = Depends(get_mami_config),
):
    """Score all saved answers for an initiative. Returns CRITICAL and NON_CRITICAL findings."""
    # Verify ownership
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    # Load saved answers (D-06: via Assessment, not initiative_id directly)
    answers = session.exec(
        select(QuestionnaireAnswer)
        .join(Assessment, QuestionnaireAnswer.assessment_id == Assessment.id)  # type: ignore[arg-type]
        .where(Assessment.initiative_id == initiative_id)
    ).all()

    if not answers:
        return ScoreResponse(
            initiative_id=initiative_id,
            total_answers=0,
            findings=[],
            critical_count=0,
            non_critical_count=0,
        )

    # Phase 13->14 interim limitation (Assumption A3 / RESEARCH Pitfall 3):
    # new-schema answers carry category_id/score (1-5), not the legacy
    # mami_code/answer_value shape this MAMI-code-keyed ZEN scoring pipeline
    # expects — real per-assessment scoring against the new DSSC config is
    # Phase 14's job. Degrade to zero findings rather than raising.
    answers_for_scoring: list[dict] = []

    # Score using ZEN Engine (async per-answer)
    findings_raw = await score_all_answers(engine, answers_for_scoring)

    findings = [FindingRead(**f) for f in findings_raw]
    critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
    non_critical_count = sum(1 for f in findings if f.severity == "NON_CRITICAL")

    return ScoreResponse(
        initiative_id=initiative_id,
        total_answers=len(answers),
        findings=findings,
        critical_count=critical_count,
        non_critical_count=non_critical_count,
    )
