import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import JwtPayload


class TokenService:

    def create_access_token(
        self,
        user_id: uuid.UUID,
        role: str,
        user_created_at: datetime | None = None,
    ) -> str:
        now    = datetime.now(tz=timezone.utc)
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload: dict[str, object] = {
            "sub":  str(user_id),
            "role": role,
            "iat":  int(now.timestamp()),
            "exp":  int(expire.timestamp()),
        }
        if user_created_at is not None:
            payload["created_at"] = int(user_created_at.replace(tzinfo=timezone.utc).timestamp())

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_access_token(self, token: str) -> JwtPayload:
        try:
            raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise exc
        return JwtPayload(**raw)

    def create_sos_token(self, user_id: uuid.UUID) -> str:
        now    = datetime.now(tz=timezone.utc)
        expire = now + timedelta(hours=24)

        payload: dict[str, object] = {
            "sub":   str(user_id),
            "scope": "sos_only",
            "iat":   int(now.timestamp()),
            "exp":   int(expire.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_sos_token(self, token: str) -> dict:
        try:
            raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise exc
        if raw.get("scope") != "sos_only":
            raise JWTError("Not a SOS token")
        return raw

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        repo: RefreshTokenRepository,
    ) -> str:
        raw_token  = str(uuid.uuid4())
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
        await repo.revoke(old_token)
        return await self.create_refresh_token(user_id, repo)