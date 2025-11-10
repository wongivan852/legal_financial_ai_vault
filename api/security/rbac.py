"""
Role-Based Access Control (RBAC)
Decorators and functions for permission checking
"""

from typing import List
from fastapi import Depends, HTTPException, status
from functools import wraps

from models.user import User, UserRole
from security.auth import get_current_user


def require_role(allowed_roles: List[UserRole]):
    """
    Decorator to require specific user roles for an endpoint

    Usage:
        @app.get("/admin/users")
        def get_users(current_user: User = Depends(require_role([UserRole.ADMIN]))):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role - convenience function"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_analyst_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require analyst or admin role"""
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or Admin access required"
        )
    return current_user


class Permission:
    """Permission definitions for the application"""

    # Document permissions
    VIEW_DOCUMENTS = "view_documents"
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    PROCESS_DOCUMENTS = "process_documents"

    # AI Agent permissions
    USE_AGENTS = "use_agents"
    VIEW_AGENT_RESULTS = "view_agent_results"

    # User management permissions
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    ASSIGN_ROLES = "assign_roles"

    # System permissions
    VIEW_AUDIT_LOGS = "view_audit_logs"
    VIEW_SYSTEM_HEALTH = "view_system_health"
    MANAGE_SYSTEM = "manage_system"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    UserRole.VIEWER: [
        Permission.VIEW_DOCUMENTS,
        Permission.VIEW_AGENT_RESULTS,
    ],
    UserRole.ANALYST: [
        Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.PROCESS_DOCUMENTS,
        Permission.USE_AGENTS,
        Permission.VIEW_AGENT_RESULTS,
    ],
    UserRole.ADMIN: [
        # Admins have all permissions
        Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.PROCESS_DOCUMENTS,
        Permission.USE_AGENTS,
        Permission.VIEW_AGENT_RESULTS,
        Permission.VIEW_USERS,
        Permission.MANAGE_USERS,
        Permission.ASSIGN_ROLES,
        Permission.VIEW_AUDIT_LOGS,
        Permission.VIEW_SYSTEM_HEALTH,
        Permission.MANAGE_SYSTEM,
    ],
}


def has_permission(user: User, permission: str) -> bool:
    """
    Check if user has a specific permission

    Args:
        user: User object
        permission: Permission string from Permission class

    Returns:
        True if user has permission, False otherwise
    """
    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions


def check_permission(user: User, permission: str):
    """
    Check permission and raise exception if not authorized

    Args:
        user: User object
        permission: Permission string from Permission class

    Raises:
        HTTPException: If user doesn't have permission
    """
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission}"
        )


def require_permission(permission: str):
    """
    Decorator to require a specific permission

    Usage:
        @app.delete("/documents/{id}")
        def delete_document(
            id: str,
            current_user: User = Depends(require_permission(Permission.DELETE_DOCUMENTS))
        ):
            ...
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        check_permission(current_user, permission)
        return current_user

    return permission_checker


def check_resource_ownership(user: User, resource_owner_id: str):
    """
    Check if user owns a resource or is an admin

    Args:
        user: Current user
        resource_owner_id: ID of the resource owner

    Raises:
        HTTPException: If user doesn't own resource and is not admin
    """
    if user.role != UserRole.ADMIN and user.id != resource_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
