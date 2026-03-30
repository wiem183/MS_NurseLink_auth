import uuid
from datetime import datetime, timezone

import pytest

from app.models.user import User
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.password_service import PasswordService


class DummyUserRepo(UserRepository):
    async def find_by_email(self, email: str):
        return None


class DummyRefreshRepo(RefreshTokenRepository):
    async def create(self, rt):
        return rt


class DummyPasswordService(PasswordService):
    def hash_password(self, pw: str):
        return pw

    def verify_password(self, pw: str, hashed: str) -> bool:
        return pw == hashed


@pytest.mark.asyncio
async def test_issue_tokens_includes_creation_date():
    # set up service with dummies; we only call the private helper directly
    auth = AuthService(
        user_repo=DummyUserRepo(),
        token_repo=DummyRefreshRepo(),
        token_service=TokenService(),
        password_service=DummyPasswordService(),
    )

    now = datetime.now(tz=timezone.utc)
    user = User(
        email="a@b.com",
        password_hash="pw",
        first_name="F",
        last_name="L",
        phone=None,
        role="ADMIN",
    )
    user.id = uuid.uuid4()
    user.created_at = now

    dto = await auth._issue_tokens(user)
    # decoded inside _issue_tokens already happened by TokenService test;
    # ensure DTO token is parseable and contains the timestamp.
    payload = auth.token_service.verify_access_token(dto.access_token)
    assert payload.created_at == int(now.timestamp())
