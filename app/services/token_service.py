import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import JwtPayload


class TokenService:
    # ── Access token ──────────────────────────────────────────────────────────

    def create_access_token(self, user_id: uuid.UUID, role: str) -> str:
        """Sign and return a short-lived JWT access token."""
        now = datetime.now(tz=timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_access_token(self, token: str) -> JwtPayload:
        """
        Decode and validate a JWT access token.
        Raises jose.JWTError (→ caught by the guard and re-raised as 401).
        """
        try:
            raw = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except JWTError as exc:
            raise exc  # guard converts this to HTTP 401

        return JwtPayload(**raw)

    # ── Refresh token ─────────────────────────────────────────────────────────

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        repo: RefreshTokenRepository,
    ) -> str:
        """
        Generate a random opaque refresh token, persist it, and return the
        raw value (stored/sent to client; only the raw value is stored, not hashed,
        because we need to look it up directly — keep DB encrypted at rest).
        """
        raw_token = str(uuid.uuid4())  # opaque, random
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        rt = RefreshToken(
            user_id=user_id,
            token=raw_token,
            expires_at=expires_at,
            is_revoked=False,
            is_one_time_use=True,
        )
        await repo.create(rt)
        return raw_token

    async def verify_refresh_token(
        self,
        raw_token: str,
        repo: RefreshTokenRepository,
    ) -> RefreshToken:
        """
        Validate a refresh token string.
        Returns the RefreshToken ORM object so the caller can rotate / revoke it.
        Raises ValueError with a descriptive message on any failure.
        """
        rt = await repo.find_by_token(raw_token)

        if rt is None:
            raise ValueError("Refresh token not found.")
        if rt.is_revoked:
            raise ValueError("Refresh token has been revoked.")
        if rt.is_expired():
            raise ValueError("Refresh token has expired.")

        return rt

    async def rotate_refresh_token(
        self,
        old_token: str,
        user_id: uuid.UUID,
        repo: RefreshTokenRepository,
    ) -> str:
        """Revoke the old token and issue a fresh one (token rotation)."""
        await repo.revoke(old_token)
        return await self.create_refresh_token(user_id, repo)
