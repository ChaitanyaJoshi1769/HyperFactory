"""Authentication and authorization middleware"""

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.auth_service import AuthService
from app.models.user import User

security = HTTPBearer()


# ============================================================================
# Current User Dependency
# ============================================================================

def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    Raises 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = AuthService.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (redundant check, but explicit for code clarity).
    """
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify they are an admin.
    Raises 403 if user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# ============================================================================
# API Key Authentication
# ============================================================================

def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from API key (X-API-Key header).
    Raises 401 if key is invalid or user not found.
    Raises 403 if user is inactive.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required (X-API-Key header)",
        )

    user_id = AuthService.verify_api_key(db, x_api_key)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    user = AuthService.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def get_current_user_from_jwt_or_api_key(
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from either JWT token (Bearer) or API key (X-API-Key).
    Supports both authentication methods for maximum flexibility.
    Raises 401 if both methods fail or neither is provided.
    """
    # Try JWT first
    if credentials:
        token = credentials.credentials
        user_id = AuthService.verify_user_token(token)

        if user_id:
            user = AuthService.get_user(db, user_id)
            if user and user.is_active:
                return user

    # Try API key
    if x_api_key:
        user_id = AuthService.verify_api_key(db, x_api_key)

        if user_id:
            user = AuthService.get_user(db, user_id)
            if user and user.is_active:
                return user

    # Both failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials (provide Bearer token or X-API-Key header)",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================

def require_role(required_role: str):
    """
    Create a dependency that ensures user has the specified role.

    Usage:
        @router.get("/admin")
        def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}",
            )
        return current_user

    return role_checker


def require_any_role(*required_roles: str):
    """
    Create a dependency that ensures user has one of the specified roles.

    Usage:
        @router.get("/managers")
        def manager_endpoint(user: User = Depends(require_any_role("admin", "manager"))):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            roles_str = ", ".join(required_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required one of roles: {roles_str}",
            )
        return current_user

    return role_checker


def require_permission(permission: str):
    """
    Create a dependency that checks user permissions.

    Supported permissions:
    - "manage_users": admin only
    - "manage_suppliers": admin, manager
    - "manage_factory": admin, manager, engineer
    - "manage_quotes": admin, manager
    """
    permission_roles = {
        "manage_users": ["admin"],
        "manage_suppliers": ["admin", "manager"],
        "manage_factory": ["admin", "manager", "engineer"],
        "manage_quotes": ["admin", "manager"],
    }

    allowed_roles = permission_roles.get(permission, [])

    if not allowed_roles:
        raise ValueError(f"Unknown permission: {permission}")

    return require_any_role(*allowed_roles)


# ============================================================================
# Optional Authentication (returns None if not authenticated)
# ============================================================================

def get_optional_current_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Attempt to get current user from JWT token, but don't fail if not present.
    Returns None if unauthenticated, User if authenticated.
    """
    if not credentials:
        return None

    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        return None

    user = AuthService.get_user(db, user_id)

    if not user or not user.is_active:
        return None

    return user


# ============================================================================
# Token User ID Extraction (for internal use)
# ============================================================================

def get_current_user_id(
    credentials: HTTPAuthCredentials = Depends(security),
) -> UUID:
    """
    Extract user ID from JWT token without database lookup.
    Useful for audit logging or when only the ID is needed.
    """
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
