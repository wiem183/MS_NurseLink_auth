import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_auth_service
from app.guards.jwt_auth_guard import get_current_user
from app.models.user import User
from app.schemas.auth import AuthResponseDto, LoginDto, RegisterDto
from app.schemas.token import PasswordResetRequestDto, RefreshTokenDto, ResetPasswordDto
from app.schemas.user import UserDto
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=AuthResponseDto,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
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


@router.post(
    "/password-reset/request",
    summary="Request a password-reset email",
)
async def request_password_reset(
    body: PasswordResetRequestDto,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    msg = await auth_service.request_password_reset(body.email)
    return {"message": msg}


@router.post(
    "/password-reset/confirm",
    summary="Confirm password reset with token",
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
    await auth_service.reset_password(body.token, body.new_password, body.confirm_password)
    return {"message": "Password reset successfully."}


# ── Protected endpoints (require valid JWT) ───────────────────────────────────

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
