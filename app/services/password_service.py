import secrets

from passlib.context import CryptContext

from app.core.config import settings


class PasswordService:
    def __init__(self) -> None:
        self._ctx = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.BCRYPT_ROUNDS,
        )


    def hash_password(self, plain: str) -> str:
        return self._ctx.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return self._ctx.verify(plain, hashed)


    @staticmethod
    def generate_reset_token(nbytes: int = 32) -> str:
        """URL-safe random token for password reset links."""
        return secrets.token_urlsafe(nbytes)

    @staticmethod
    def generate_verification_token(nbytes: int = 32) -> str:
        """URL-safe random token for email verification links."""
        return secrets.token_urlsafe(nbytes)
