from pydantic import BaseModel, Field


class RefreshTokenDto(BaseModel):
    """Body for POST /auth/refresh."""

    refresh_token: str


class ResetPasswordDto(BaseModel):
    """Body for POST /auth/password-reset/confirm."""

    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    def passwords_match(self) -> bool:
        return self.new_password == self.confirm_password


class PasswordResetRequestDto(BaseModel):
    """Body for POST /auth/password-reset/request."""

    email: str
