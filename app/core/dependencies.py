# app/api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.password_service import PasswordService
from app.services.role_service import RoleService
from app.services.token_service import TokenService
from app.services.user_service import UserService


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_token_repository(
    user_repo: UserRepository = Depends(get_user_repository),  # ← same session
) -> RefreshTokenRepository:
    return RefreshTokenRepository(user_repo.db)  # ← reuse user_repo's db


def get_password_service() -> PasswordService:
    return PasswordService()


def get_token_service() -> TokenService:
    return TokenService()


def get_role_service() -> RoleService:
    return RoleService()


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repo)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_repo: RefreshTokenRepository = Depends(get_token_repository),
    token_service: TokenService = Depends(get_token_service),
    password_service: PasswordService = Depends(get_password_service),
) -> AuthService:
    return AuthService(user_repo, token_repo, token_service, password_service)