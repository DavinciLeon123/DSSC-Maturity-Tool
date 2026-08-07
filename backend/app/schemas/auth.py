from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator

COMMON_PASSWORDS = {
    "password",
    "12345678",
    "123456789",
    "qwerty123",
    "admin1234",
    "letmein1",
    "welcome1",
    "monkey123",
    "password1",
    "iloveyou1",
}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    participant_type: Literal["DSI", "SP"] = "DSI"
    data_consent: bool

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Password is too common — choose a stronger password")
        return v

    @field_validator("data_consent")
    @classmethod
    def validate_data_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must agree to data collection to register")
        return v


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    participant_type: str | None  # D-12/Pitfall 5 — nullable on the model now
    created_at: str  # ISO format


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v
