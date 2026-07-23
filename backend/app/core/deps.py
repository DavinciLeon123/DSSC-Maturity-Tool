import zen
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    sub = decode_access_token(token)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.exec(select(User).where(User.email == sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_zen_engine(request: Request) -> zen.ZenEngine:
    """FastAPI dependency: returns the ZEN Engine singleton from app.state."""
    return request.app.state.zen_engine


def get_mami_config(request: Request) -> dict:
    """FastAPI dependency: returns the loaded mami-framework.json dict."""
    return request.app.state.mami_config


def get_questionnaire_config(request: Request) -> dict:
    """FastAPI dependency: returns the loaded questionnaire-v1.json dict (legacy)."""
    return request.app.state.questionnaire_config


def get_questionnaire_configs(request: Request) -> dict:
    """FastAPI dependency: returns both v2 questionnaire configs as {"DSI": {...}, "SP": {...}}."""
    return request.app.state.questionnaire_configs


def get_dssc_questionnaire_config(request: Request) -> dict:
    """FastAPI dependency: returns the universal DSSC questionnaire config
    (52 questions / 6 categories) cached at lifespan startup. No
    participant_type selection — this config is served identically to every
    caller (D-10, QSTN-04)."""
    return request.app.state.dssc_questionnaire_config
