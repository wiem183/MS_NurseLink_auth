import uuid
from datetime import datetime

from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponseDto, LoginDto, RegisterDto
from app.services.password_service import PasswordService
from app.services.token_service import TokenService


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        token_service: TokenService,
        password_service: PasswordService,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.token_service = token_service
        self.password_service = password_service


    async def register(self, dto: RegisterDto) -> AuthResponseDto:
        # 1. Check uniqueness
        existing = await self.user_repo.find_by_email(dto.email.lower())
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with that email already exists.",
            )

        # 2. Hash password & persist user
        user = User(
            email=dto.email.lower(),
            password_hash=self.password_service.hash_password(dto.password),
            first_name=dto.first_name,
            last_name=dto.last_name,
            phone=dto.phone,
            role=dto.role,
        )
        user = await self.user_repo.create(user)

        # 3. Issue tokens
        return await self._issue_tokens(user)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, dto: LoginDto) -> AuthResponseDto:
        # 1. Look up user
        user = await self.user_repo.find_by_email(dto.email.lower())
        if not user or not self.password_service.verify_password(
            dto.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # 2. Check active status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support.",
            )

        # 3. Update last login timestamp
        user.last_login_at = datetime.utcnow()
        await self.user_repo.save(user)

        # 4. Issue tokens
        return await self._issue_tokens(user)

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh(self, raw_token: str) -> AuthResponseDto:
        try:
            rt = await self.token_service.verify_refresh_token(
                raw_token, self.token_repo
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            )

        user = await self.user_repo.find_by_id(rt.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive."
            )

        # Rotate: revoke old, issue new pair
        new_refresh = await self.token_service.rotate_refresh_token(
            raw_token, user.id, self.token_repo
        )
        access = self.token_service.create_access_token(user.id, user.role.value)

        return self._build_response(user, access, new_refresh)

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, raw_token: str) -> None:
        """Revoke the refresh token — access token expires naturally."""
        await self.token_repo.revoke(raw_token)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        """Revoke every session for this user (logout from all devices)."""
        await self.token_repo.revoke_all_for_user(user_id)

    # ── Password reset ────────────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> str:
        """
        Generate a reset token and return it.
        In production: send via email. Returning here for testability.
        """
        user = await self.user_repo.find_by_email(email.lower())
        if not user:
            # Don't reveal whether email exists
            return "If that email exists you will receive a reset link."

        token = self.password_service.generate_reset_token()
        # TODO: persist token with expiry in a password_reset_tokens table
        # TODO: send email with the token
        return token

    async def reset_password(
        self, token: str, new_password: str, confirm_password: str
    ) -> None:
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match.",
            )
        # TODO: look up token → get user → update password_hash
        # Placeholder until password_reset_tokens table is added
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password reset requires the reset-token table (see TODO).",
        )

    # ── Get current user ──────────────────────────────────────────────────────

    async def get_me(self, user: User) -> User:
        return user

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _issue_tokens(self, user: User) -> AuthResponseDto:
        access = self.token_service.create_access_token(user.id, user.role.value)
        refresh = await self.token_service.create_refresh_token(
            user.id, self.token_repo
        )
        return self._build_response(user, access, refresh)

    @staticmethod
    def _build_response(user: User, access: str, refresh: str) -> AuthResponseDto:
        return AuthResponseDto(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            access_token=access,
            refresh_token=refresh,
        )
