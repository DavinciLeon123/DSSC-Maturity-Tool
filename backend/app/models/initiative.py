from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class InitiativeStatus(str, Enum):
    draft = "draft"
    active = "active"
    submitted = "submitted"


class ParticipantType(str, Enum):
    dsi = "DSI"
    sp = "SP"


# Predefined sector list — from research open question recommendation
SECTOR_OPTIONS = [
    "Healthcare",
    "Finance",
    "Government",
    "Energy",
    "Education",
    "Transport",
    "Agriculture",
    "Other",
]


class Initiative(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)  # unique = one per user
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    sector: str  # Must be in SECTOR_OPTIONS
    sector_other: str | None = None  # Required if sector == "Other"
    contact_name: str | None = None
    contact_email: str | None = None
    organization: str | None = None
    participant_type: ParticipantType = Field(default=ParticipantType.dsi)
    status: InitiativeStatus = Field(default=InitiativeStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
