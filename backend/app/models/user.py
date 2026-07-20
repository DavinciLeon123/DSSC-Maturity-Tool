from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="USER")  # "USER" or "ADMIN"
    participant_type: str = Field(default="DSI")  # "DSI" or "SP"
    failed_login_attempts: int = Field(default=0)
    lockout_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
