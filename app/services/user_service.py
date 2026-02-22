import uuid

from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UpdateUserDto, UserDto
from app.models.enums import UserRole


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    # ── Queries ───────────────────────────────────────────────────────────────

    async def find_all(self) -> list[UserDto]:
        users = await self.user_repo.find_all()
        return [UserDto.model_validate(u) for u in users]

    async def find_by_id(self, user_id: uuid.UUID) -> UserDto:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserDto.model_validate(user)

    async def find_by_id_raw(self, user_id: uuid.UUID) -> User:
        """Return the ORM object (used internally by other services)."""
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    async def find_by_email(self, email: str) -> User | None:
        return await self.user_repo.find_by_email(email)

    # ── Mutations ─────────────────────────────────────────────────────────────

    async def update_profile(
        self, user_id: uuid.UUID, dto: UpdateUserDto
    ) -> UserDto:
        user = await self.user_repo.update_profile(user_id, dto)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserDto.model_validate(user)

    async def activate(self, user_id: uuid.UUID) -> UserDto:
        user = await self.find_by_id_raw(user_id)
        user.activate()
        saved = await self.user_repo.save(user)
        return UserDto.model_validate(saved)

    async def deactivate(self, user_id: uuid.UUID) -> UserDto:
        user = await self.find_by_id_raw(user_id)
        user.deactivate()
        saved = await self.user_repo.save(user)
        return UserDto.model_validate(saved)

    async def verify_email(self, user_id: uuid.UUID) -> None:
        user = await self.find_by_id_raw(user_id)
        user.verify_email()
        await self.user_repo.save(user)

    async def promote(self, user_id: uuid.UUID, new_role: UserRole) -> UserDto:
        """Change a user's role (e.g. PATIENT → NURSE, NURSE → ADMIN)."""
        user = await self.find_by_id_raw(user_id)
        user.role = new_role
        saved = await self.user_repo.save(user)
        return UserDto.model_validate(saved)

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self.find_by_id_raw(user_id)
        await self.user_repo.delete(user)
