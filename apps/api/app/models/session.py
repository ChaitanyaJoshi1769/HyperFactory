"""Session model for tracking active user sessions"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db import Base


class Session(Base):
    """Session model for tracking active user sessions"""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_token = Column(String(500), unique=True, nullable=False, index=True)

    # Device information
    device_id = Column(String(255), index=True)  # Fingerprint of device
    device_name = Column(String(255))  # e.g., "Chrome on Windows"
    user_agent = Column(Text)  # Full user agent string

    # Location and network info
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4 or IPv6
    country = Column(String(100))  # Geographic location
    city = Column(String(100))

    # Session lifecycle
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)  # Last request time
    expires_at = Column(DateTime, nullable=False, index=True)  # Session expiration
    revoked_at = Column(DateTime)  # When session was manually revoked
    revoke_reason = Column(String(255))  # Why session was revoked

    # Security flags
    is_trusted = Column(Boolean, default=False)  # User marked as trusted device
    suspicious_activity = Column(Boolean, default=False)  # Flagged for review
