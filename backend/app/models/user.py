from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="USER")  # "USER" or "ADMIN"
    # Nullable per D-12 so legacy users the migration tags with NULL remain
    # valid — this only relaxed the NOT NULL constraint. UserCreate still
    # defaults new registrations to a concrete "DSI"/"SP" value; nothing
    # currently stops populating it going forward (WR-04).
    participant_type: str | None = Field(default=None)
    # Default True is deliberate and load-bearing: every pre-existing
    # direct User(...) construction site (make_user/_create_authed_user/
    # create_admin, and any legacy row backfilled by the migration) is
    # treated as already consented, per D-05/REQ-1 — only new registrations
    # go through UserCreate's stricter no-default validator below.
    data_consent: bool = Field(default=True)
    failed_login_attempts: int = Field(default=0)
    lockout_until: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    password_reset_token: str | None = None
    password_reset_expires: datetime | None = None
