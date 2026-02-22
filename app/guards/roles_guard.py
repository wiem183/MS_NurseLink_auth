from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.guards.jwt_auth_guard import get_current_user
from app.models.enums import UserRole
from app.models.user import User


def require_roles(*roles: UserRole) -> Callable:
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_roles(UserRole.ADMIN))
        ): ...
    """
    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user

    return _check


# Pre-built shorthand guards for the most common role combinations
require_admin = require_roles(UserRole.ADMIN)
require_nurse = require_roles(UserRole.NURSE, UserRole.ADMIN)
require_patient = require_roles(UserRole.PATIENT, UserRole.ADMIN)
