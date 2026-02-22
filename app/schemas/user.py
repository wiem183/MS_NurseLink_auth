import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class UserDto(BaseModel):
    """Safe public view of a user — no password hash."""

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_email_verified: bool
    profile_picture_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserDto(BaseModel):
    """All fields optional — PATCH semantics."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    profile_picture_url: str | None = Field(default=None, max_length=500)
