"""User model for authentication"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class User(Base):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(50), default="user")  # user, admin, engineer, manager
    organization = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_locked = Column(Boolean, default=False, index=True)
    locked_until = Column(DateTime)  # When the lock expires (auto-unlock)
    email_verified = Column(Boolean, default=False, index=True)
    email_verified_at = Column(DateTime)


class APIKey(Base):
    """API Key model for programmatic access"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)
