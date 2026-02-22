from app.models.enums import UserRole
from app.models.user import User


class RoleService:
    """
    Stateless helper for role-based permission checks.
    Used by the RolesGuard dependency.
    """

    @staticmethod
    def has_permission(user: User, required_roles: tuple[UserRole, ...]) -> bool:
        """Return True if user's role is in the set of required roles."""
        return user.role in required_roles

    @staticmethod
    def is_admin(user: User) -> bool:
        return user.role == UserRole.ADMIN

    @staticmethod
    def is_nurse(user: User) -> bool:
        return user.role == UserRole.NURSE

    @staticmethod
    def is_patient(user: User) -> bool:
        return user.role == UserRole.PATIENT

    @staticmethod
    def is_owner_or_admin(user: User, resource_user_id: object) -> bool:
        """Allow access if the user owns the resource or is an admin."""
        return str(user.id) == str(resource_user_id) or user.role == UserRole.ADMIN
