import secrets
import resend
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token
)
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead, ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# Dummy hash for timing-attack prevention (prevents username enumeration)
_DUMMY_HASH = hash_password("dummy-timing-equalization-string")
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRead)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        participant_type=user_in.participant_type,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead(id=user.id, email=user.email, role=user.role,
                    participant_type=user.participant_type,
                    created_at=user.created_at.isoformat())


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.email == form_data.username)).first()

    # Always verify (even for non-existent user) to prevent timing attacks
    if user is None:
        verify_password(form_data.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check account lockout
    now = datetime.now(timezone.utc)
    if user.lockout_until and user.lockout_until.replace(tzinfo=timezone.utc) > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again after {user.lockout_until.isoformat()}",
        )

    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.lockout_until = datetime.utcnow() + timedelta(minutes=_LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        session.add(user)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Successful login — reset lockout state
    user.failed_login_attempts = 0
    user.lockout_until = None
    session.add(user)
    session.commit()

    return Token(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        participant_type=current_user.participant_type,
        created_at=current_user.created_at.isoformat(),
    )


def _send_reset_email(email: str, token: str, frontend_url: str, api_key: str) -> None:
    """Send plain-text password reset email via Resend. Falls back to log-only if no API key."""
    import logging
    reset_url = f"{frontend_url}/reset-password?token={token}"
    if not api_key:
        print(f"[DEV] Password reset link for {email}: {reset_url}", flush=True)
        return
    resend.api_key = api_key
    params: resend.Emails.SendParams = {
        "from": "MaMi Checker <onboarding@resend.dev>",
        "to": [email],
        "subject": "Reset your MaMi Checker password",
        "text": (
            f"Hi,\n\n"
            f"You requested a password reset for your MaMi Checker account.\n\n"
            f"Click the link below to set a new password:\n{reset_url}\n\n"
            f"This link expires in 30 minutes. If you did not request this, "
            f"you can safely ignore this email.\n\n"
            f"The MaMi Checker team"
        ),
    }
    resend.Emails.send(params)


@router.post("/forgot-password", status_code=202)
def forgot_password(
    email_in: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Trigger password reset email. Always returns 202 — never reveals whether email is registered.
    Enforces 60-second cooldown: if a token was issued less than 60 seconds ago, returns 429."""
    user = session.exec(select(User).where(User.email == email_in.email)).first()
    if user:
        # 60-second cooldown: derive token created_at from expires - 30 min
        if user.password_reset_expires is not None:
            token_created_at = user.password_reset_expires - timedelta(minutes=30)
            if datetime.utcnow() < token_created_at + timedelta(seconds=60):
                raise HTTPException(
                    status_code=429,
                    detail="Please wait before requesting another reset link."
                )
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(minutes=30)
        session.add(user)
        session.commit()
        background_tasks.add_task(
            _send_reset_email,
            user.email,
            token,
            settings.FRONTEND_URL,
            settings.RESEND_API_KEY,
        )
    return {"message": "If this email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
def reset_password(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_session),
):
    """Validate reset token and set new password. Token is invalidated immediately after use."""
    user = session.exec(
        select(User).where(User.password_reset_token == payload.token)
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if (
        user.password_reset_expires is None
        or user.password_reset_expires < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None      # Invalidate — one-time use only
    user.password_reset_expires = None
    session.add(user)
    session.commit()
    return {"message": "Password reset successfully. Please log in with your new password."}
