"""Authentication router - login, registration, token management"""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db import get_db
from app.schemas.auth import UserCreate, UserRead, UserLogin, TokenResponse, APIKeyCreate, APIKeyRead
from app.services.auth_service import AuthService
from app.security import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()


# ============================================================================
# User Registration & Login
# ============================================================================

@router.post("/register", response_model=UserRead, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        db_user = AuthService.create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and get access token"""
    user = AuthService.authenticate_user(db, credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = AuthService.create_access_token_for_user(
        user,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserRead)
def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = AuthService.get_user(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ============================================================================
# User Profile Management
# ============================================================================

@router.put("/me", response_model=UserRead)
def update_current_user(
    update_data: dict,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = AuthService.update_user(
        db,
        user_id,
        full_name=update_data.get("full_name"),
        organization=update_data.get("organization"),
        password=update_data.get("password")
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ============================================================================
# API Key Management
# ============================================================================

@router.post("/api-keys", response_model=dict, status_code=201)
def create_api_key(
    key_data: APIKeyCreate,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new API key for programmatic access"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = AuthService.get_user(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    api_key, key_value = AuthService.create_api_key(
        db,
        user_id,
        key_data.name,
        key_data.expires_at
    )

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": key_value,  # Only shown once
        "created_at": api_key.created_at.isoformat(),
        "message": "Save this key securely. You won't be able to see it again."
    }


@router.get("/api-keys")
def list_api_keys(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List all API keys for current user"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

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


@router.delete("/api-keys/{key_id}", status_code=204)
def delete_api_key(
    key_id: str,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    from uuid import UUID
    success = AuthService.delete_api_key(db, UUID(key_id))

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")


@router.post("/api-keys/{key_id}/revoke", status_code=204)
def revoke_api_key(
    key_id: str,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    token = credentials.credentials
    user_id = AuthService.verify_user_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    from uuid import UUID
    success = AuthService.revoke_api_key(db, UUID(key_id))

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")


# ============================================================================
# Token Refresh (Future)
# ============================================================================

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Refresh access token (future implementation)"""
    # This endpoint is a placeholder for future refresh token support
    # Current implementation uses long-lived tokens
    raise HTTPException(status_code=501, detail="Not implemented yet")
