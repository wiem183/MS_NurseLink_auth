import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UpdateUserDto


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def find_all(self) -> list[User]:
        result = await self.db.execute(select(User))
        return list(result.scalars().all())

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()


    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()   # get the generated id without committing
        await self.db.refresh(user)
        return user

    async def update_profile(
        self, user_id: uuid.UUID, dto: UpdateUserDto
    ) -> User | None:
        # Only send non-None fields to the DB
        values: dict[str, Any] = {
            k: v for k, v in dto.model_dump().items() if v is not None
        }
        if not values:
            return await self.find_by_id(user_id)

        await self.db.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await self.db.flush()
        return await self.find_by_id(user_id)

    async def update_profile_url(
        self, user_id: uuid.UUID, url: str
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(profile_picture_url=url)
        )
        await self.db.flush()

    async def save(self, user: User) -> User:
        """Persist changes already made to a tracked User instance."""
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()
