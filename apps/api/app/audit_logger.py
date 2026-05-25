"""Audit logging for security events"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json
import logging
from uuid import UUID


class AuditEventType(str, Enum):
    """Types of audit events"""

    # Authentication events
    USER_REGISTERED = "user:registered"
    USER_LOGIN = "user:login"
    USER_LOGIN_FAILED = "user:login_failed"
    USER_LOGOUT = "user:logout"
    USER_PASSWORD_CHANGED = "user:password_changed"
    USER_PASSWORD_RESET = "user:password_reset"
    API_KEY_CREATED = "api_key:created"
    API_KEY_DELETED = "api_key:deleted"
    API_KEY_REVOKED = "api_key:revoked"

    # User management events
    USER_ACTIVATED = "user:activated"
    USER_DEACTIVATED = "user:deactivated"
    USER_DELETED = "user:deleted"
    USER_ROLE_CHANGED = "user:role_changed"
    USER_ADMIN_STATUS_CHANGED = "user:admin_status_changed"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "ratelimit:exceeded"
    RATE_LIMIT_RESET = "ratelimit:reset"

    # Security events
    SUSPICIOUS_ACTIVITY = "security:suspicious_activity"
    ACCOUNT_LOCKOUT = "security:account_lockout"
    PERMISSION_DENIED = "security:permission_denied"

    # Data events
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_DELETE = "data:delete"


class AuditEventSeverity(str, Enum):
    """Severity levels for audit events"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditEvent:
    """Structured audit event"""

    def __init__(
        self,
        event_type: AuditEventType,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        severity: AuditEventSeverity = AuditEventSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        source_ip: Optional[str] = None,
        status: str = "success",
    ):
        """
        Create an audit event.

        Args:
            event_type: Type of event
            actor_id: User ID performing the action
            resource_id: ID of resource being accessed
            resource_type: Type of resource (user, api_key, etc.)
            action: Action performed (create, update, delete, etc.)
            severity: Event severity level
            details: Additional event details
            source_ip: IP address of request source
            status: Event status (success, failure, blocked)
        """
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.actor_id = str(actor_id) if actor_id else None
        self.resource_id = str(resource_id) if resource_id else None
        self.resource_type = resource_type
        self.action = action
        self.severity = severity
        self.details = details or {}
        self.source_ip = source_ip
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "action": self.action,
            "severity": self.severity.value,
            "details": self.details,
            "source_ip": self.source_ip,
            "status": self.status,
        }

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Audit logging system"""

    def __init__(self, logger_name: str = "hyperfactory.audit"):
        """
        Initialize audit logger.

        Args:
            logger_name: Name for the Python logger
        """
        self.logger = logging.getLogger(logger_name)

        # Set up file handler if not already configured
        if not self.logger.handlers:
            handler = logging.FileHandler("logs/audit.log")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: AuditEvent to log
        """
        log_level = getattr(
            logging, event.severity.value.upper(), logging.INFO
        )
        self.logger.log(log_level, event.to_json())

    def log_user_registered(
        self, user_id: str, username: str, email: str, source_ip: Optional[str] = None
    ) -> None:
        """Log user registration"""
        event = AuditEvent(
            event_type=AuditEventType.USER_REGISTERED,
            actor_id=user_id,
            resource_id=user_id,
            resource_type="user",
            action="create",
            severity=AuditEventSeverity.INFO,
            details={"username": username, "email": email},
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_user_login(
        self, user_id: str, username: str, source_ip: Optional[str] = None
    ) -> None:
        """Log successful user login"""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=user_id,
            resource_id=user_id,
            resource_type="user",
            action="login",
            severity=AuditEventSeverity.INFO,
            details={"username": username},
            source_ip=source_ip,
            status="success",
        )
        self.log_event(event)

    def log_user_login_failed(
        self, username: str, reason: str = "invalid_credentials", source_ip: Optional[str] = None
    ) -> None:
        """Log failed login attempt"""
        event = AuditEvent(
            event_type=AuditEventType.USER_LOGIN_FAILED,
            resource_type="user",
            action="login",
            severity=AuditEventSeverity.WARNING,
            details={"username": username, "reason": reason},
            source_ip=source_ip,
            status="failure",
        )
        self.log_event(event)

    def log_rate_limit_exceeded(
        self, identifier: str, limit_type: str, source_ip: Optional[str] = None
    ) -> None:
        """Log rate limit exceeded event"""
        event = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            resource_type="rate_limit",
            severity=AuditEventSeverity.WARNING,
            details={"identifier": identifier, "limit_type": limit_type},
            source_ip=source_ip,
            status="blocked",
        )
        self.log_event(event)

    def log_user_password_changed(
        self, user_id: str, username: str, source_ip: Optional[str] = None
    ) -> None:
        """Log password change"""
        event = AuditEvent(
            event_type=AuditEventType.USER_PASSWORD_CHANGED,
            actor_id=user_id,
            resource_id=user_id,
            resource_type="user",
            action="update",
            severity=AuditEventSeverity.INFO,
            details={"username": username},
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_api_key_created(
        self,
        user_id: str,
        key_id: str,
        key_name: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log API key creation"""
        event = AuditEvent(
            event_type=AuditEventType.API_KEY_CREATED,
            actor_id=user_id,
            resource_id=key_id,
            resource_type="api_key",
            action="create",
            severity=AuditEventSeverity.INFO,
            details={"key_name": key_name, "user_id": user_id},
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_api_key_deleted(
        self,
        user_id: str,
        key_id: str,
        key_name: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log API key deletion"""
        event = AuditEvent(
            event_type=AuditEventType.API_KEY_DELETED,
            actor_id=user_id,
            resource_id=key_id,
            resource_type="api_key",
            action="delete",
            severity=AuditEventSeverity.WARNING,
            details={"key_name": key_name, "user_id": user_id},
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_api_key_revoked(
        self,
        user_id: str,
        key_id: str,
        key_name: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log API key revocation"""
        event = AuditEvent(
            event_type=AuditEventType.API_KEY_REVOKED,
            actor_id=user_id,
            resource_id=key_id,
            resource_type="api_key",
            action="revoke",
            severity=AuditEventSeverity.WARNING,
            details={"key_name": key_name, "user_id": user_id},
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_permission_denied(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str,
        required_permission: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log permission denied event"""
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_DENIED,
            actor_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            severity=AuditEventSeverity.WARNING,
            details={"required_permission": required_permission},
            source_ip=source_ip,
            status="denied",
        )
        self.log_event(event)

    def log_user_deleted(
        self,
        admin_id: str,
        deleted_user_id: str,
        deleted_username: str,
        reason: Optional[str] = None,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log user deletion"""
        event = AuditEvent(
            event_type=AuditEventType.USER_DELETED,
            actor_id=admin_id,
            resource_id=deleted_user_id,
            resource_type="user",
            action="delete",
            severity=AuditEventSeverity.CRITICAL,
            details={
                "deleted_username": deleted_username,
                "admin_id": admin_id,
                "reason": reason,
            },
            source_ip=source_ip,
        )
        self.log_event(event)

    def log_suspicious_activity(
        self,
        user_id: Optional[str],
        activity_type: str,
        description: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log suspicious activity"""
        event = AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            actor_id=user_id,
            severity=AuditEventSeverity.CRITICAL,
            details={
                "activity_type": activity_type,
                "description": description,
            },
            source_ip=source_ip,
        )
        self.log_event(event)


# Global audit logger instance
audit_logger = AuditLogger()
