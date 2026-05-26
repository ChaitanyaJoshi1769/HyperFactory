"""Webhook and event management models"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Integer, Enum, Uuid
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from app.db import Base


class WebhookEventType(str, enum.Enum):
    """Supported webhook event types"""
    # Factory events
    FACTORY_CREATED = "factory.created"
    FACTORY_UPDATED = "factory.updated"
    FACTORY_DELETED = "factory.deleted"

    # Machine events
    MACHINE_CREATED = "machine.created"
    MACHINE_UPDATED = "machine.updated"
    MACHINE_DELETED = "machine.deleted"

    # Production job events
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"

    # CAD analysis events
    CAD_ANALYSIS_COMPLETED = "cad.analysis_completed"
    CAD_ANALYSIS_FAILED = "cad.analysis_failed"

    # Hardware part events
    PART_CREATED = "part.created"
    PART_UPDATED = "part.updated"
    PART_DELETED = "part.deleted"

    # Supplier events
    SUPPLIER_CREATED = "supplier.created"
    SUPPLIER_UPDATED = "supplier.updated"
    SUPPLIER_DELETED = "supplier.deleted"

    # Supplier quote events
    QUOTE_CREATED = "quote.created"
    QUOTE_UPDATED = "quote.updated"
    QUOTE_DELETED = "quote.deleted"

    # User/account events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"


class WebhookStatus(str, enum.Enum):
    """Webhook status"""
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILED = "failed"


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String(2000), nullable=False)
    secret = Column(String(255), nullable=False)  # For HMAC signature
    status = Column(String(50), default="active", index=True)
    description = Column(String(500))

    # Event subscription
    events = Column(JSON, default=list)  # List of event types to subscribe to

    # Retry configuration
    max_retries = Column(Integer, default=5)
    retry_delay_seconds = Column(Integer, default=60)
    timeout_seconds = Column(Integer, default=30)

    # Stats
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    last_delivery_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    last_failure_reason = Column(String(500))

    # Management
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)  # Soft delete support

    # Relationships
    user = relationship("User", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_id = Column(Uuid, ForeignKey("webhooks.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    delivery_id = Column(String(64), unique=True, index=True)  # Unique delivery ID for idempotency

    # Payload
    payload = Column(JSON, nullable=False)

    # Delivery status
    status = Column(String(50), default="pending", index=True)  # pending, success, failed, timeout
    http_status_code = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(String(1000))

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    next_retry_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_attempted_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_id = Column(Uuid, ForeignKey("webhooks.id"), nullable=False, index=True)
    delivery_id = Column(String(64), ForeignKey("webhook_deliveries.delivery_id"))

    # Log details
    action = Column(String(100), nullable=False)  # created, delivered, failed, retried, disabled
    status_code = Column(Integer)
    response_body = Column(String(5000))
    error_details = Column(String(1000))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    webhook = relationship("Webhook")
