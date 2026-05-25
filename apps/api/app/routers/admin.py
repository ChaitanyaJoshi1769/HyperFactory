"""Admin management router - user and system administration"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.db import get_db
from app.models.user import User
from app.schemas.auth import UserRead
from app.middleware import get_current_admin_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# User Management (Admin Only)
# ============================================================================

@router.get("/users", response_model=List[UserRead])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    List all users with pagination (admin only).

    Query Parameters:
    - skip: Number of users to skip (default: 0)
    - limit: Number of users to return (default: 100, max: 1000)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get user by ID (admin only)"""
    user = AuthService.get_user(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.patch("/users/{user_id}/admin", response_model=UserRead)
def set_admin_status(
    user_id: UUID,
    is_admin: bool,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Set admin status for a user (admin only).

    Request body:
    {
      "is_admin": true/false
    }
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing self as admin
    if not is_admin and user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove admin status from yourself"
        )

    user.is_admin = is_admin
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserRead)
def set_user_role(
    user_id: UUID,
    role: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Set user role (admin only).

    Valid roles: user, admin, engineer, manager

    Request body:
    {
      "role": "engineer"
    }
    """
    valid_roles = ["user", "admin", "engineer", "manager"]

    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/activate", response_model=UserRead)
def activate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Activate a user (admin only)"""
    success = AuthService.activate_user(db, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    user = AuthService.get_user(db, user_id)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate a user (admin only).

    Deactivated users cannot login but their data is preserved.
    """
    # Prevent deactivating self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself"
        )

    success = AuthService.deactivate_user(db, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    user = AuthService.get_user(db, user_id)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a user (admin only).

    CAUTION: This action cannot be undone. All user data will be deleted.
    """
    # Prevent deleting self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete associated API keys first
    db.query(APIKey).filter(APIKey.user_id == user_id).delete()

    # Delete user
    db.delete(user)
    db.commit()


# ============================================================================
# API Key Management (Admin)
# ============================================================================

@router.get("/users/{user_id}/api-keys")
def list_user_api_keys(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """List all API keys for a specific user (admin only)"""
    # Verify user exists
    user = AuthService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    api_keys = AuthService.list_user_api_keys(db, user_id)
    return [
        {
            "id": str(key.id),
            "name": key.name,
            "is_active": key.is_active,
            "last_used": key.last_used.isoformat() if key.last_used else None,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        }
        for key in api_keys
    ]


@router.delete("/users/{user_id}/api-keys/{key_id}", status_code=204)
def delete_user_api_key(
    user_id: UUID,
    key_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a user's API key (admin only)"""
    from app.models.user import APIKey

    # Verify user exists
    user = AuthService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify API key belongs to user
    api_key = db.query(APIKey).filter(
        (APIKey.id == key_id) & (APIKey.user_id == user_id)
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(api_key)
    db.commit()


# ============================================================================
# System Statistics
# ============================================================================

@router.get("/stats")
def get_system_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Get system-wide statistics (admin only)"""
    from app.models.hardware import HardwarePart, Material
    from app.models.supplier import Supplier
    from app.models.factory import Factory, Machine, ProductionJob
    from app.models.cad import CADModel

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()

    total_parts = db.query(HardwarePart).count()
    total_materials = db.query(Material).count()
    total_suppliers = db.query(Supplier).count()
    total_factories = db.query(Factory).count()
    total_machines = db.query(Machine).count()
    total_jobs = db.query(ProductionJob).count()
    completed_jobs = db.query(ProductionJob).filter(
        ProductionJob.status == "completed"
    ).count()
    total_cad_models = db.query(CADModel).count()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users,
        },
        "hardware": {
            "parts": total_parts,
            "materials": total_materials,
        },
        "supply_chain": {
            "suppliers": total_suppliers,
        },
        "manufacturing": {
            "factories": total_factories,
            "machines": total_machines,
            "jobs_total": total_jobs,
            "jobs_completed": completed_jobs,
            "jobs_in_progress": db.query(ProductionJob).filter(
                ProductionJob.status == "in_progress"
            ).count(),
            "jobs_queued": db.query(ProductionJob).filter(
                ProductionJob.status == "queued"
            ).count(),
        },
        "design": {
            "cad_models": total_cad_models,
        },
    }


# ============================================================================
# User Search & Filtering
# ============================================================================

@router.get("/users/search")
def search_users(
    query: str = Query(..., min_length=1),
    field: str = Query("username", regex="^(username|email|organization)$"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Search users by field.

    Query Parameters:
    - query: Search string (required)
    - field: Field to search (username, email, organization - default: username)
    """
    search_term = f"%{query}%"

    if field == "username":
        users = db.query(User).filter(User.username.ilike(search_term)).all()
    elif field == "email":
        users = db.query(User).filter(User.email.ilike(search_term)).all()
    elif field == "organization":
        users = db.query(User).filter(User.organization.ilike(search_term)).all()
    else:
        raise HTTPException(status_code=400, detail="Invalid field")

    return [
        {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "organization": user.organization,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


# Import at bottom to avoid circular imports
from datetime import datetime
from app.models.user import APIKey
