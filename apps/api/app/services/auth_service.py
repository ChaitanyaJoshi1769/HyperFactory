"""Authentication service - user management and JWT tokens"""

from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from datetime import timedelta

from app.models.user import User, APIKey
from app.schemas.auth import UserCreate, UserLogin
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
)


class AuthService:
    """Service layer for authentication operations"""

    # ============================================================================
    # User Management
    # ============================================================================

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user"""
        # Check if user exists
        existing = db.query(User).filter(
            (User.username == user.username) | (User.email == user.email)
        ).first()

        if existing:
            raise ValueError(f"User with username or email already exists")

        # Create user with hashed password
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            organization=user.organization,
            hashed_password=hashed_password,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def get_user(db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def authenticate_user(db: Session, login: UserLogin) -> Optional[User]:
        """Authenticate user with username and password"""
        user = AuthService.get_user_by_username(db, login.username)

        if not user:
            return None

        if not verify_password(login.password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def update_user(db: Session, user_id: UUID, full_name: Optional[str] = None,
                   organization: Optional[str] = None,
                   password: Optional[str] = None) -> Optional[User]:
        """Update user information"""
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        if full_name is not None:
            user.full_name = full_name

        if organization is not None:
            user.organization = organization

        if password is not None:
            user.hashed_password = get_password_hash(password)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def deactivate_user(db: Session, user_id: UUID) -> bool:
        """Deactivate a user"""
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return False

        user.is_active = False
        db.commit()
        return True

    @staticmethod
    def activate_user(db: Session, user_id: UUID) -> bool:
        """Activate a user"""
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return False

        user.is_active = True
        db.commit()
        return True

    # ============================================================================
    # Token Management
    # ============================================================================

    @staticmethod
    def create_access_token_for_user(user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token for a user"""
        data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin,
        }
        return create_access_token(data, expires_delta)

    @staticmethod
    def verify_user_token(token: str) -> Optional[UUID]:
        """Verify a token and return user ID"""
        user_id = verify_token(token)
        return UUID(user_id) if user_id else None

    # ============================================================================
    # API Key Management
    # ============================================================================

    @staticmethod
    def create_api_key(db: Session, user_id: UUID, name: str,
                      expires_at=None) -> APIKey:
        """Create an API key for a user"""
        from app.security import get_password_hash
        import secrets

        # Generate a random key
        key = secrets.token_urlsafe(32)
        key_hash = get_password_hash(key)

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            expires_at=expires_at,
        )

        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return api_key, key  # Return both the record and the actual key

    @staticmethod
    def verify_api_key(db: Session, key: str) -> Optional[UUID]:
        """Verify an API key and return user ID"""
        from app.security import verify_password
        from datetime import datetime

        # Find all API keys and check the hash
        api_keys = db.query(APIKey).filter(APIKey.is_active == True).all()

        for api_key in api_keys:
            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                continue

            # Verify the key
            if verify_password(key, api_key.key_hash):
                # Update last used timestamp
                api_key.last_used = datetime.utcnow()
                db.commit()
                return api_key.user_id

        return None

    @staticmethod
    def revoke_api_key(db: Session, api_key_id: UUID) -> bool:
        """Revoke an API key"""
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()

        if not api_key:
            return False

        api_key.is_active = False
        db.commit()
        return True

    @staticmethod
    def list_user_api_keys(db: Session, user_id: UUID):
        """List all API keys for a user"""
        return db.query(APIKey).filter(APIKey.user_id == user_id).all()

    @staticmethod
    def delete_api_key(db: Session, api_key_id: UUID) -> bool:
        """Delete an API key"""
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()

        if not api_key:
            return False

        db.delete(api_key)
        db.commit()
        return True
