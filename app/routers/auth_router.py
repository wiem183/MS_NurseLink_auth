# app/routers/auth_router.py
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.dependencies import get_auth_service, get_user_service
from app.guards.jwt_auth_guard import get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponseDto, LoginDto, RegisterDto
from app.schemas.token import (
    PasswordResetRequestDto,
    RefreshTokenDto,
    ResetPasswordDto,
    VerifyEmailDto,
    VerifyOTPDto,
    ResendVerificationDto,
)
from app.schemas.user import UserDto
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=AuthResponseDto,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (sends email verification OTP)",
)
async def register(
    dto: RegisterDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponseDto:
    return await auth_service.register(dto)


@router.post(
    "/login",
    response_model=AuthResponseDto,
    summary="Login with email & password",
)
async def login(
    dto: LoginDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponseDto:
    return await auth_service.login(dto)


@router.post(
    "/refresh",
    response_model=AuthResponseDto,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    body: RefreshTokenDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponseDto:
    return await auth_service.refresh(body.refresh_token)


# ── Email verification ────────────────────────────────────────────────────────

@router.post(
    "/verify-email",
    summary="Step 1 — Verify email with the OTP sent on registration",
)
async def verify_email(
    body: VerifyEmailDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Takes { email, otp } and marks the user's email as verified."""
    await auth_service.verify_email(body.email, body.otp)
    return {"message": "Email vérifié avec succès."}


@router.post(
    "/resend-verification",
    summary="Resend the email verification OTP",
)
async def resend_verification(
    body: ResendVerificationDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Sends a fresh verification OTP. Always returns 200."""
    await auth_service.resend_verification(body.email)
    return {"message": "Si cet email existe, un nouveau code a été envoyé."}


# ── Password reset (3-step OTP flow) ─────────────────────────────────────────

@router.post(
    "/password-reset/request",
    summary="Step 1 — Send password reset OTP to email",
)
async def request_password_reset(
    body: PasswordResetRequestDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    msg = await auth_service.request_password_reset(body.email)
    return {"message": msg}


@router.post(
    "/password-reset/verify-otp",
    summary="Step 2 — Verify OTP and get reset token",
)
async def verify_otp(
    body: VerifyOTPDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    reset_token = await auth_service.verify_otp(body.email, body.otp)
    return {"message": "Code vérifié avec succès.", "reset_token": reset_token}


@router.post(
    "/password-reset/confirm",
    summary="Step 3 — Set new password using reset token",
)
async def confirm_password_reset(
    body: ResetPasswordDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    if not body.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )
    await auth_service.reset_password(
        email=body.email,
        reset_token=body.reset_token,
        new_password=body.new_password,
        confirm_password=body.confirm_password,
    )
    return {"message": "Password reset successfully."}


# ── Protected endpoints ───────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserDto,
    summary="Get the currently authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserDto:
    return UserDto.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (revoke refresh token)",
)
async def logout(
    body: RefreshTokenDto,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await auth_service.logout(body.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
)
async def logout_all(
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await auth_service.logout_all(current_user.id)


# ── Internal endpoints (microservice-to-microservice, no JWT) ─────────────────

def _require_internal_key(x_internal_api_key: str = Header(...)) -> None:
    """
    Dependency that validates the shared internal API key.
    Rejects with 403 if the header is missing or wrong.
    """
    if x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key.",
        )


@router.patch(
    "/internal/activate/{user_id}",
    response_model=UserDto,
    summary="[Internal] Activate a user after KYC approval",
    tags=["Internal"],
)
async def internal_activate_user(
    user_id: uuid.UUID,
    _key: None = Depends(_require_internal_key),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    """
    Called by the KYC service when an admin approves a nurse's KYC.
    Sets is_active = True so the nurse can log in.
    """
    return await user_service.activate(user_id)


@router.patch(
    "/internal/deactivate/{user_id}",
    response_model=UserDto,
    summary="[Internal] Deactivate a user after KYC rejection",
    tags=["Internal"],
)
async def internal_deactivate_user(
    user_id: uuid.UUID,
    _key: None = Depends(_require_internal_key),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    """
    Called by the KYC service when an admin rejects a nurse's KYC.
    Sets is_active = False.
    """
    return await user_service.deactivate(user_id)