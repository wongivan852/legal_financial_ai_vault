"""
Security Module - Authentication, Authorization, and Encryption
"""

from .auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    get_current_user,
    get_current_active_user,
    authenticate_user,
)
from .rbac import (
    require_role,
    require_admin,
    require_analyst_or_admin,
    require_permission,
    has_permission,
    check_permission,
    check_resource_ownership,
    Permission,
    ROLE_PERMISSIONS,
)
from .encryption import (
    encryption_service,
    hash_string,
    hash_file,
    EncryptionService,
)

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "get_current_active_user",
    "authenticate_user",
    "require_role",
    "require_admin",
    "require_analyst_or_admin",
    "require_permission",
    "has_permission",
    "check_permission",
    "check_resource_ownership",
    "Permission",
    "ROLE_PERMISSIONS",
    "encryption_service",
    "hash_string",
    "hash_file",
    "EncryptionService",
]
