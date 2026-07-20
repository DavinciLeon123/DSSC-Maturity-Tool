from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_questionnaire_configs
from app.db.session import get_session
from app.models.initiative import Initiative
from app.models.questionnaire import QuestionnaireAnswer
from app.models.user import User
from app.schemas.questionnaire import AnswerCreate, AnswerRead

router = APIRouter(tags=["questionnaire"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/questionnaire/config")
def get_questionnaire_config_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    configs: dict = Depends(get_questionnaire_configs),
):
    """Return the v2 questionnaire config for the current user's participant type (DSI or SP)."""
    initiative = session.exec(
        select(Initiative).where(Initiative.user_id == current_user.id)
    ).first()
    if not initiative:
        raise HTTPException(
            status_code=404, detail="Create an initiative first to access the questionnaire"
        )
    participant_type = initiative.participant_type.value  # "DSI" or "SP"
    return configs[participant_type]


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
    """Upsert one answer for a question. Creates on first save, updates on subsequent saves.
    Enforces ownership: current user must own the initiative."""
    # Verify initiative ownership
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    # PostgreSQL upsert (insert or update on conflict)
    stmt = pg_insert(QuestionnaireAnswer).values(
        initiative_id=initiative_id,
        question_id=question_id,
        mami_code=answer_in.mami_code,
        questionnaire_version=answer_in.questionnaire_version,
        answer_value=answer_in.answer_value,
        followup_selections=answer_in.followup_selections,
        followup_other=answer_in.followup_other,
        answered_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_answer_per_question",
        set_={
            "answer_value": stmt.excluded.answer_value,
            "followup_selections": stmt.excluded.followup_selections,
            "followup_other": stmt.excluded.followup_other,
            "questionnaire_version": stmt.excluded.questionnaire_version,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.exec(stmt)
    session.commit()

    # Fetch and return the upserted row
    result = session.exec(
        select(QuestionnaireAnswer).where(
            QuestionnaireAnswer.initiative_id == initiative_id,
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
    """Return all saved answers for an initiative (for save/resume — QUES-02)."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")

    answers = session.exec(
        select(QuestionnaireAnswer).where(QuestionnaireAnswer.initiative_id == initiative_id)
    ).all()
    return answers
