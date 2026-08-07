from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.deps import get_current_user, get_dssc_questionnaire_config
from app.db.session import get_session
from app.models.initiative import Initiative
from app.models.user import User
from app.services.dimension_scoring import assert_assessment_complete, compute_dimension_scores

router = APIRouter(tags=["scoring"])


class DimensionScore(BaseModel):
    category_id: str
    name: str
    score: float


class ScoreResponse(BaseModel):
    initiative_id: int
    dimension_scores: list[DimensionScore]


@router.post("/initiatives/{initiative_id}/score", response_model=ScoreResponse)
def score_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    config: dict = Depends(get_dssc_questionnaire_config),
):
    """Score the initiative's current draft Assessment against the 6 DSSC
    maturity dimensions (D-04, SCOR-01/02).

    Verifies ownership first (404 when the initiative doesn't exist, 403
    when it isn't the caller's), THEN enforces the SCOR-04 completion gate
    (422 "Questionnaire not fully answered" when no draft assessment exists
    or it isn't 100% answered) — ordering matters so a caller can never
    distinguish "not yours" from "not complete" (T-14-01). On success,
    returns one equal-weight per-category average per dimension, in config
    category order.
    """
    # Verify ownership
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    assessment = assert_assessment_complete(session, initiative_id, config)
    scores = compute_dimension_scores(session, assessment.id, config)  # type: ignore[arg-type]

    return ScoreResponse(
        initiative_id=initiative_id,
        dimension_scores=[DimensionScore(**s) for s in scores],
    )
