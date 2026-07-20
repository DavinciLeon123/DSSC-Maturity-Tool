from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from app.db.session import get_session
from app.core.deps import get_current_user, get_zen_engine, get_mami_config
from app.models.user import User
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.services.scoring_engine import score_all_answers
import zen

router = APIRouter(tags=["scoring"])


class FindingRead(BaseModel):
    mami_code: str
    severity: str   # "CRITICAL" | "NON_CRITICAL" | ""
    status: str     # "FINDING" | "COMPLIANT" | "NOT_APPLICABLE"


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

    # Load saved answers
    answers = session.exec(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.initiative_id == initiative_id
        )
    ).all()

    if not answers:
        return ScoreResponse(
            initiative_id=initiative_id,
            total_answers=0,
            findings=[],
            critical_count=0,
            non_critical_count=0,
        )

    # Build MAMI code lookup: {code_id: {moscow_level, critical_override}}
    code_lookup = {
        code["id"]: {
            "moscow_level": code["moscow_level"],
            "critical_override": code.get("critical_override"),
        }
        for code in mami_config.get("codes", [])
    }

    # Prepare answer dicts for scoring (join answer with MAMI code metadata)
    answers_for_scoring = []
    for answer in answers:
        code_meta = code_lookup.get(answer.mami_code, {})
        answers_for_scoring.append({
            "mami_code": answer.mami_code,
            "moscow_level": code_meta.get("moscow_level", "SHOULD"),
            "answer_value": answer.answer_value,
            "critical_override": code_meta.get("critical_override"),
        })

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
