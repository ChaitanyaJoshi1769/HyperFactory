"""Session Management - Track active user sessions and device access"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from sqlalchemy.orm import Session as DBSession
from app.models import Session, User
from app.audit_logger import audit_logger, AuditEventType, AuditEventSeverity
from app.email_verification import EmailTokenManager
import os
import json

# Session configuration
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
SESSION_EXPIRATION_HOURS = int(os.getenv("SESSION_EXPIRATION_HOURS", "24"))  # Default 24 hours
SESSION_IDLE_TIMEOUT_HOURS = int(os.getenv("SESSION_IDLE_TIMEOUT_HOURS", "8"))  # Logout after 8 hours idle


class DeviceFingerprint:
    """Generate and validate device fingerprints"""

    @staticmethod
    def generate_fingerprint(user_agent: str, accept_language: str = None) -> str:
        """
        Generate a device fingerprint from user agent and other signals.

        Args:
            user_agent: Browser/app user agent string
            accept_language: Accept-Language header for language preference

        Returns:
            Base32-encoded fingerprint hash
        """
        fingerprint_data = f"{user_agent}:{accept_language or ''}"
        hash_obj = hashlib.sha256(fingerprint_data.encode())
        return hash_obj.hexdigest()[:16]  # First 16 chars of hash

    @staticmethod
    def extract_device_name(user_agent: str) -> str:
        """
        Extract human-readable device name from user agent.

        Examples:
        - "Chrome on Windows"
        - "Safari on macOS"
        - "Mobile Safari on iOS"

        Args:
            user_agent: User agent string

        Returns:
            Human-readable device name
        """
        if not user_agent:
            return "Unknown Device"

        # Extract browser
        browser = "Unknown"
        if "Chrome" in user_agent and "Chromium" not in user_agent:
            browser = "Chrome"
        elif "Firefox" in user_agent:
            browser = "Firefox"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
        elif "Opera" in user_agent:
            browser = "Opera"

        # Extract OS
        os_name = "Unknown OS"
        if "Windows" in user_agent:
            os_name = "Windows"
        elif "Macintosh" in user_agent:
            os_name = "macOS"
        elif "Linux" in user_agent:
            os_name = "Linux"
        elif "Android" in user_agent:
            os_name = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            os_name = "iOS"

        return f"{browser} on {os_name}"


class SessionManager:
    """Manages user sessions for authentication and device tracking"""

    def __init__(self):
        """Initialize session manager"""
        self.secret_key = SESSION_SECRET_KEY
        self.token_manager = EmailTokenManager(SESSION_SECRET_KEY, SESSION_EXPIRATION_HOURS / 60)
        self.max_sessions_per_user = 10  # Limit concurrent sessions

    def create_session(
        self,
        db: DBSession,
        user: User,
        ip_address: str,
        user_agent: str = None,
        accept_language: str = None,
        source_ip: str = None,
    ) -> Tuple[str, Session]:
        """
        Create a new session for user login.

        Args:
            db: Database session
            user: User object
            ip_address: Client IP address
            user_agent: Browser/app user agent
            accept_language: Accept-Language header
            source_ip: Audit logging source IP

        Returns:
            Tuple of (session_token, session_object)
        """
        # Generate secure session token
        session_token = secrets.token_urlsafe(32)

        # Generate device fingerprint
        device_fingerprint = DeviceFingerprint.generate_fingerprint(user_agent, accept_language)
        device_name = DeviceFingerprint.extract_device_name(user_agent or "")

        # Calculate session expiration
        expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRATION_HOURS)

        # Create session record
        session = Session(
            user_id=user.id,
            session_token=session_token,
            device_id=device_fingerprint,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
            last_activity=datetime.utcnow(),
            is_active=True,
            is_trusted=False,
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # Audit log: session created
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(user.id),
            resource_id=str(session.id),
            resource_type="session",
            action="create_session",
            severity=AuditEventSeverity.INFO,
            details={
                "user_id": str(user.id),
                "username": user.username,
                "device": device_name,
                "ip_address": ip_address,
            },
            source_ip=source_ip,
        )

        # Check for concurrent session limit
        active_sessions = db.query(Session).filter(
            Session.user_id == user.id,
            Session.is_active == True,
            Session.expires_at > datetime.utcnow(),
        ).count()

        if active_sessions > self.max_sessions_per_user:
            # Revoke oldest session
            oldest = db.query(Session).filter(
                Session.user_id == user.id,
                Session.is_active == True,
                Session.expires_at > datetime.utcnow(),
            ).order_by(Session.created_at).first()

            if oldest:
                self.revoke_session(db, oldest.id, "Exceeded max concurrent sessions", source_ip)

        return session_token, session

    def validate_session(
        self,
        db: DBSession,
        session_token: str,
        ip_address: str = None,
        require_ip_match: bool = False,
        source_ip: str = None,
    ) -> Tuple[bool, Optional[Session], str]:
        """
        Validate a session token.

        Args:
            db: Database session
            session_token: Token to validate
            ip_address: Current IP address (optional, for validation)
            require_ip_match: Whether IP must match original
            source_ip: Audit logging source IP

        Returns:
            Tuple of (is_valid, session_object, message)
        """
        if not session_token:
            return False, None, "Session token required"

        # Lookup session
        session = db.query(Session).filter(Session.session_token == session_token).first()

        if not session:
            return False, None, "Invalid session token"

        if not session.is_active:
            return False, None, "Session has been revoked"

        # Check expiration
        if session.expires_at <= datetime.utcnow():
            session.is_active = False
            db.commit()
            return False, None, "Session has expired"

        # Check idle timeout
        idle_time = datetime.utcnow() - session.last_activity
        if idle_time > timedelta(hours=SESSION_IDLE_TIMEOUT_HOURS):
            self.revoke_session(db, session.id, "Idle timeout", source_ip)
            return False, None, "Session idle timeout"

        # IP address validation (optional)
        if require_ip_match and ip_address and session.ip_address != ip_address:
            # Log suspicious activity
            audit_logger.log_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                actor_id=str(session.user_id),
                resource_id=str(session.id),
                resource_type="session",
                action="ip_mismatch",
                severity=AuditEventSeverity.WARNING,
                details={
                    "original_ip": session.ip_address,
                    "current_ip": ip_address,
                    "device": session.device_name,
                },
                source_ip=source_ip,
            )
            session.suspicious_activity = True
            db.commit()

            return False, None, "IP address mismatch"

        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()

        return True, session, "Session valid"

    def get_active_sessions(
        self,
        db: DBSession,
        user_id: str,
    ) -> List[Dict]:
        """
        Get all active sessions for a user.

        Args:
            db: Database session
            user_id: User ID (as string)

        Returns:
            List of session details (active only)
        """
        sessions = db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True,
            Session.expires_at > datetime.utcnow(),
        ).order_by(Session.last_activity.desc()).all()

        return [
            {
                "id": str(session.id),
                "device_name": session.device_name,
                "ip_address": session.ip_address,
                "country": session.country,
                "city": session.city,
                "is_trusted": session.is_trusted,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "suspicious_activity": session.suspicious_activity,
            }
            for session in sessions
        ]

    def revoke_session(
        self,
        db: DBSession,
        session_id: str,
        reason: str = None,
        source_ip: str = None,
    ) -> bool:
        """
        Revoke a session (logout).

        Args:
            db: Database session
            session_id: Session ID to revoke
            reason: Reason for revocation
            source_ip: Audit logging source IP

        Returns:
            True if revoked successfully
        """
        session = db.query(Session).filter(Session.id == session_id).first()

        if not session:
            return False

        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.revoke_reason = reason or "User logout"
        db.commit()

        # Audit log: session revoked
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(session.user_id),
            resource_id=str(session.id),
            resource_type="session",
            action="revoke_session",
            severity=AuditEventSeverity.INFO,
            details={
                "user_id": str(session.user_id),
                "reason": session.revoke_reason,
                "device": session.device_name,
            },
            source_ip=source_ip,
        )

        return True

    def revoke_all_user_sessions(
        self,
        db: DBSession,
        user_id: str,
        reason: str = None,
        source_ip: str = None,
    ) -> int:
        """
        Revoke all active sessions for a user (force logout everywhere).

        Args:
            db: Database session
            user_id: User ID
            reason: Reason for revocation
            source_ip: Audit logging source IP

        Returns:
            Number of sessions revoked
        """
        sessions = db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_active == True,
        ).all()

        count = 0
        for session in sessions:
            self.revoke_session(db, str(session.id), reason, source_ip)
            count += 1

        return count

    def trust_device(
        self,
        db: DBSession,
        session_id: str,
        source_ip: str = None,
    ) -> bool:
        """
        Mark a device as trusted (user chose "Remember this device").

        Args:
            db: Database session
            session_id: Session ID
            source_ip: Audit logging source IP

        Returns:
            True if marked successfully
        """
        session = db.query(Session).filter(Session.id == session_id).first()

        if not session:
            return False

        session.is_trusted = True
        db.commit()

        # Audit log: device trusted
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(session.user_id),
            resource_id=str(session.id),
            resource_type="session",
            action="trust_device",
            severity=AuditEventSeverity.INFO,
            details={
                "device": session.device_name,
                "ip_address": session.ip_address,
            },
            source_ip=source_ip,
        )

        return True

    def get_suspicious_sessions(
        self,
        db: DBSession,
        user_id: str,
    ) -> List[Dict]:
        """
        Get sessions flagged for suspicious activity.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of suspicious session details
        """
        sessions = db.query(Session).filter(
            Session.user_id == user_id,
            Session.suspicious_activity == True,
        ).order_by(Session.last_activity.desc()).all()

        return [
            {
                "id": str(session.id),
                "device_name": session.device_name,
                "ip_address": session.ip_address,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
            }
            for session in sessions
        ]

    def cleanup_expired_sessions(
        self,
        db: DBSession,
    ) -> int:
        """
        Mark expired sessions as inactive (cleanup task).

        Args:
            db: Database session

        Returns:
            Number of sessions cleaned up
        """
        expired = db.query(Session).filter(
            Session.is_active == True,
            Session.expires_at <= datetime.utcnow(),
        ).all()

        count = 0
        for session in expired:
            session.is_active = False
            db.commit()
            count += 1

        return count


# Global session manager instance
session_manager = SessionManager()
