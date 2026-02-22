import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ─────────────────────────────────────────────────────────────────

    async def find_by_token(self, token: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def find_by_user_id(self, user_id: uuid.UUID) -> list[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        return list(result.scalars().all())

    # ── Write ────────────────────────────────────────────────────────────────

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def revoke(self, token: str) -> None:
        """Revoke a single token by its raw value."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(is_revoked=True)
        )
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke every active refresh token for a user (e.g. on logout all)."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self.db.flush()

    async def mark_as_used(self, token: str) -> None:
        """Mark a one-time-use token as revoked after it has been consumed."""
        await self.revoke(token)

    async def delete_expired(self) -> None:
        """Housekeeping: remove tokens past their expiry date."""
        await self.db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await self.db.flush()

    async def is_expired(self, token: str) -> bool:
        rt = await self.find_by_token(token)
        if rt is None:
            return True
        return rt.is_expired()
