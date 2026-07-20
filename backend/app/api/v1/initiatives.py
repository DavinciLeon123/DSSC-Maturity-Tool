from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.initiative import Initiative, InitiativeStatus
from app.models.user import User
from app.schemas.initiative import InitiativeCreate, InitiativeRead, InitiativeUpdate

router = APIRouter(prefix="/initiatives", tags=["initiatives"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InitiativeRead)
def create_initiative(
    initiative_in: InitiativeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(Initiative).where(Initiative.user_id == current_user.id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a registered initiative. Only one initiative per user is allowed in this version.",
        )
    initiative = Initiative(
        user_id=current_user.id,
        participant_type=current_user.participant_type,
        **initiative_in.model_dump()
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
):
    """Mark initiative as submitted. Idempotent — re-submitting an already-submitted initiative is OK."""
    initiative = session.get(Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    if initiative.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your initiative")
    initiative.status = InitiativeStatus.submitted
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)
    session.commit()
    return {"message": "Initiative submitted successfully", "status": initiative.status.value}


def _to_read(i: Initiative) -> InitiativeRead:
    return InitiativeRead(
        id=i.id, user_id=i.user_id, name=i.name, description=i.description,
        sector=i.sector, sector_other=i.sector_other, contact_name=i.contact_name,
        contact_email=i.contact_email, organization=i.organization,
        participant_type=i.participant_type.value,
        status=i.status.value, created_at=i.created_at.isoformat(),
        updated_at=i.updated_at.isoformat(),
    )
