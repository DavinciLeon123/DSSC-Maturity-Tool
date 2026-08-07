from pydantic import BaseModel, EmailStr, field_validator

from app.models.initiative import SECTOR_OPTIONS, InitiativeStatus


class InitiativeCreate(BaseModel):
    name: str
    description: str | None = None
    sector: str
    sector_other: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    organization: str | None = None
    # participant_type removed — read from current_user.participant_type at creation time

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str) -> str:
        if v not in SECTOR_OPTIONS:
            raise ValueError(f"sector must be one of: {', '.join(SECTOR_OPTIONS)}")
        return v

    @field_validator("sector_other")
    @classmethod
    def validate_sector_other(cls, v: str | None, info) -> str | None:
        sector = info.data.get("sector")
        if sector == "Other" and not v:
            raise ValueError("sector_other is required when sector is 'Other'")
        return v


class InitiativeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sector: str | None = None
    sector_other: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    organization: str | None = None
    status: InitiativeStatus | None = None
    # participant_type intentionally excluded — not editable after creation


class InitiativeRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    sector: str
    sector_other: str | None
    contact_name: str | None
    contact_email: str | None
    organization: str | None
    participant_type: str | None  # D-12/Pitfall 5 — nullable on the model now
    status: str
    created_at: str
    updated_at: str
