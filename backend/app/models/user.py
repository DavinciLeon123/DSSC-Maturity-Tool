from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="USER")  # "USER" or "ADMIN"
    participant_type: str = Field(default="DSI")  # "DSI" or "SP"
    failed_login_attempts: int = Field(default=0)
    lockout_until: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    password_reset_token: str | None = None
    password_reset_expires: datetime | None = None
