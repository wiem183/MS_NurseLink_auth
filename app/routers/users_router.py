import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_user_service
from app.guards.jwt_auth_guard import get_current_user
from app.guards.roles_guard import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UpdateUserDto, UserDto
from app.services.role_service import RoleService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


# ── Admin-only ────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[UserDto],
    summary="List all users (admin only)",
)
async def get_all_users(
    _admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> list[UserDto]:
    return await user_service.find_all()


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (admin only)",
)
async def delete_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> None:
    await user_service.delete(user_id)


@router.patch(
    "/{user_id}/activate",
    response_model=UserDto,
    summary="Activate a user account (admin only)",
)
async def activate_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    return await user_service.activate(user_id)


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserDto,
    summary="Deactivate a user account (admin only)",
)
async def deactivate_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    return await user_service.deactivate(user_id)


@router.patch(
    "/{user_id}/promote",
    response_model=UserDto,
    summary="Change a user's role (admin only)",
)
async def promote_user(
    user_id: uuid.UUID,
    new_role: UserRole,
    _admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    return await user_service.promote(user_id, new_role)


# ── Authenticated (owner or admin) ────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=UserDto,
    summary="Get user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    if not RoleService.is_owner_or_admin(current_user, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile.",
        )
    return await user_service.find_by_id(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserDto,
    summary="Update user profile",
)
async def update_user(
    user_id: uuid.UUID,
    dto: UpdateUserDto,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserDto:
    if not RoleService.is_owner_or_admin(current_user, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own profile.",
        )
    return await user_service.update_profile(user_id, dto)
