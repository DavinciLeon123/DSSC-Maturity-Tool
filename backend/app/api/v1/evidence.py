from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.models.initiative import Initiative
from app.models.evidence import EvidenceURL
from app.schemas.evidence import EvidenceCreate, EvidenceRead

router = APIRouter(tags=["evidence"])


@router.post("/initiatives/{initiative_id}/evidence", response_model=EvidenceRead)
def submit_evidence(
    initiative_id: int,
    evidence_in: EvidenceCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")

    evidence = EvidenceURL(
        initiative_id=initiative_id,
        question_id=evidence_in.question_id,
        mami_code=evidence_in.mami_code,
        url=evidence_in.url,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


@router.delete("/initiatives/{initiative_id}/evidence/{evidence_id}")
def delete_evidence(
    initiative_id: int,
    evidence_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")
    evidence = session.get(EvidenceURL, evidence_id)
    if not evidence or evidence.initiative_id != initiative_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    session.delete(evidence)
    session.commit()
    return {"ok": True}


@router.get("/initiatives/{initiative_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    initiative_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    initiative = session.get(Initiative, initiative_id)
    if not initiative or initiative.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Initiative not found")
    evidence = session.exec(
        select(EvidenceURL).where(EvidenceURL.initiative_id == initiative_id)
    ).all()
    return evidence
