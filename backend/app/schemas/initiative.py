from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from app.models.initiative import InitiativeStatus, SECTOR_OPTIONS


class InitiativeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sector: str
    sector_other: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    organization: Optional[str] = None
    # participant_type removed — read from current_user.participant_type at creation time

    @field_validator("sector")
    @classmethod
    def validate_sector(cls, v: str) -> str:
        if v not in SECTOR_OPTIONS:
            raise ValueError(f"sector must be one of: {', '.join(SECTOR_OPTIONS)}")
        return v

    @field_validator("sector_other")
    @classmethod
    def validate_sector_other(cls, v: Optional[str], info) -> Optional[str]:
        sector = info.data.get("sector")
        if sector == "Other" and not v:
            raise ValueError("sector_other is required when sector is 'Other'")
        return v


class InitiativeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    sector_other: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    organization: Optional[str] = None
    status: Optional[InitiativeStatus] = None
    # participant_type intentionally excluded — not editable after creation


class InitiativeRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    sector: str
    sector_other: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    organization: Optional[str]
    participant_type: str
    status: str
    created_at: str
    updated_at: str
