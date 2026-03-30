# app/schemas/token.py
from pydantic import BaseModel, Field


class RefreshTokenDto(BaseModel):
    """Body for POST /auth/refresh."""
    refresh_token: str


class PasswordResetRequestDto(BaseModel):
    """Body for POST /auth/password-reset/request."""
    email: str


class VerifyOTPDto(BaseModel):
    """Body for POST /auth/password-reset/verify-otp."""
    email: str
    otp: str


class ResetPasswordDto(BaseModel):
    """Body for POST /auth/password-reset/confirm."""
    email: str
    reset_token: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str

    def passwords_match(self) -> bool:
        return self.new_password == self.confirm_password


class VerifyEmailDto(BaseModel):
    """Body for POST /auth/verify-email."""
    email: str
    otp: str


class ResendVerificationDto(BaseModel):
    """Body for POST /auth/resend-verification."""
    email: str