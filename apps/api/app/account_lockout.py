"""Account lockout mechanism for brute-force protection"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User
from app.audit_logger import audit_logger, AuditEvent, AuditEventType, AuditEventSeverity


class AccountLockoutManager:
    """Manages account lockout after repeated failed login attempts"""

    def __init__(
        self,
        max_failed_attempts: int = 5,
        lockout_duration_minutes: int = 30,
    ):
        """
        Initialize account lockout manager.

        Args:
            max_failed_attempts: Number of failed attempts before lockout (default 5)
            lockout_duration_minutes: How long to lock the account (default 30 minutes)
        """
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration_minutes = lockout_duration_minutes

    def is_account_locked(self, db: Session, user_id: str) -> bool:
        """
        Check if account is currently locked.

        Args:
            db: Database session
            user_id: User UUID to check

        Returns:
            True if account is locked, False otherwise
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check if account is locked
        if not user.is_locked:
            return False

        # Check if lock has expired
        if user.locked_until and datetime.utcnow() >= user.locked_until:
            # Auto-unlock
            self.unlock_account(db, user_id)
            return False

        return True

    def lock_account(
        self,
        db: Session,
        user: User,
        source_ip: str = None,
        reason: str = "too_many_failed_attempts",
    ) -> None:
        """
        Lock a user account.

        Args:
            db: Database session
            user: User object to lock
            source_ip: IP address that triggered the lockout
            reason: Reason for lockout
        """
        user.is_locked = True
        user.locked_until = datetime.utcnow() + timedelta(
            minutes=self.lockout_duration_minutes
        )
        db.commit()

        # Audit log: account lockout
        event = AuditEvent(
            event_type=AuditEventType.ACCOUNT_LOCKOUT,
            actor_id=str(user.id),
            resource_id=str(user.id),
            resource_type="user",
            action="lock",
            severity=AuditEventSeverity.CRITICAL,
            details={
                "username": user.username,
                "reason": reason,
                "locked_until": user.locked_until.isoformat(),
            },
            source_ip=source_ip,
        )
        audit_logger.log_event(event)

    def unlock_account(self, db: Session, user_id: str) -> None:
        """
        Unlock a user account.

        Args:
            db: Database session
            user_id: User UUID to unlock
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_locked = False
            user.locked_until = None
            db.commit()

    def record_failed_login(
        self,
        db: Session,
        user: User,
        failed_attempts: int,
        source_ip: str = None,
    ) -> bool:
        """
        Record a failed login attempt and lock account if threshold exceeded.

        Args:
            db: Database session
            user: User object
            failed_attempts: Number of failed attempts so far (from rate limiter)
            source_ip: IP address of failed attempt

        Returns:
            True if account was locked, False otherwise
        """
        # Lock account if threshold exceeded
        if failed_attempts >= self.max_failed_attempts:
            self.lock_account(
                db,
                user,
                source_ip=source_ip,
                reason=f"too_many_failed_attempts ({failed_attempts})",
            )
            return True

        return False

    def get_lockout_status(self, db: Session, user_id: str) -> dict:
        """
        Get account lockout status.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Dictionary with lockout status and remaining time
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"locked": False}

        # Check if lock has expired
        if user.is_locked and user.locked_until:
            if datetime.utcnow() >= user.locked_until:
                self.unlock_account(db, user_id)
                return {"locked": False}

            # Calculate remaining time
            remaining = (user.locked_until - datetime.utcnow()).total_seconds()
            return {
                "locked": True,
                "locked_until": user.locked_until.isoformat(),
                "seconds_remaining": max(0, int(remaining)),
            }

        return {"locked": user.is_locked if user.is_locked else False}


# Global account lockout manager instance
account_lockout_manager = AccountLockoutManager(
    max_failed_attempts=5,
    lockout_duration_minutes=30,
)
