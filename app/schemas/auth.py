
# app/schemas/auth.py
import uuid

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole


# ── Incoming DTOs ─────────────────────────────────────────────────────────────

class RegisterDto(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    role: UserRole = UserRole.PATIENT

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if not v:
            return v
        if not v.startswith("+"):
            raise ValueError(
                "Must be in international E.164 format (e.g. +21612345678)."
            )
        try:
            num = phonenumbers.parse(v, None)
        except phonenumbers.NumberParseException as e:
            raise ValueError(f"Invalid number: {e}")
        if not phonenumbers.is_valid_number(num):
            raise ValueError("Invalid phone number.")
        typ = phonenumbers.number_type(num)
        if typ not in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE):
            raise ValueError("Number must be a mobile number.")
        # Normalize to strict E.164 before storing
        return phonenumbers.format_number(num, PhoneNumberFormat.E164)


class LoginDto(BaseModel):
    email: EmailStr
    password: str


class JwtPayload(BaseModel):
    sub: str        # user id (UUID as string)
    role: UserRole
    exp: int        # unix timestamp
    iat: int        # issued at
    created_at: int # unix timestamp of user account creation


class AuthResponseDto(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = {"from_attributes": True}
