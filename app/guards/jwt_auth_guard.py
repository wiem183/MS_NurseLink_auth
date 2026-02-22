import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.dependencies import get_token_service, get_user_repository
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService

# Tells FastAPI where clients send their token (used for /docs Authorize UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    token_service: TokenService = Depends(get_token_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Core authentication dependency.
    Validates the Bearer JWT and returns the live User ORM object.
    Raises HTTP 401 on any failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = token_service.verify_access_token(token)
    except JWTError:
        raise credentials_exception

    user = await user_repo.find_by_id(uuid.UUID(payload.sub))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user
