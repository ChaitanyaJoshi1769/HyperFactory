"""Password reset token generation and password reset workflow"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models import User
from app.email_verification import EmailTokenManager, EmailVerificationService
from app.audit_logger import audit_logger, AuditEvent, AuditEventType, AuditEventSeverity
import os


# Secret key for password reset tokens (can be same as email verification or separate)
PASSWORD_RESET_SECRET_KEY = os.getenv("PASSWORD_RESET_SECRET_KEY") or os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Token expiration time (default 1 hour for password resets - shorter than email verification)
PASSWORD_RESET_TOKEN_EXPIRATION_HOURS = 1


class PasswordResetManager:
    """Manages password reset workflow with email-based tokens"""

    def __init__(
        self,
        secret_key: str = PASSWORD_RESET_SECRET_KEY,
        expiration_hours: int = PASSWORD_RESET_TOKEN_EXPIRATION_HOURS,
    ):
        """
        Initialize password reset manager.

        Args:
            secret_key: Secret key for token signing
            expiration_hours: How long tokens are valid (default 1 hour)
        """
        self.token_manager = EmailTokenManager(secret_key, expiration_hours)
        self.expiration_hours = expiration_hours

    def generate_reset_token(self, email: str) -> str:
        """
        Generate a password reset token.

        Args:
            email: Email address requesting reset

        Returns:
            Signed reset token
        """
        return self.token_manager.generate_verification_token(email)

    def verify_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token and return email.

        Args:
            token: Token to verify

        Returns:
            Email address if valid, None if invalid or expired
        """
        return self.token_manager.verify_token(token)

    def is_token_valid(self, token: str) -> bool:
        """
        Check if a password reset token is valid.

        Args:
            token: Token to check

        Returns:
            True if valid and not expired, False otherwise
        """
        return self.token_manager.is_token_valid(token)

    def request_password_reset(
        self,
        db: Session,
        email: str,
        source_ip: str = None,
    ) -> tuple[Optional[str], bool]:
        """
        Process a password reset request.

        Args:
            db: Database session
            email: Email of account requesting reset
            source_ip: IP address of request

        Returns:
            Tuple of (reset_token, user_found)
            - Token is generated if user found, None otherwise
            - user_found indicates if email exists in system
        """
        # Look up user by email
        user = db.query(User).filter(User.email == email).first()

        if user:
            # Generate reset token
            token = self.generate_reset_token(email)

            # Audit log: password reset requested
            audit_logger.log_event(
                event_type=AuditEventType.USER_PASSWORD_RESET,
                actor_id=str(user.id),
                resource_id=str(user.id),
                resource_type="user",
                action="request",
                severity=AuditEventSeverity.INFO,
                details={"email": email},
                source_ip=source_ip,
                status="success",
            )

            return token, True
        else:
            # Audit log: password reset requested for non-existent account
            # Log without actor_id since we don't know the user
            audit_logger.log_event(
                event_type=AuditEventType.USER_PASSWORD_RESET,
                resource_type="user",
                action="request",
                severity=AuditEventSeverity.WARNING,
                details={"email": email, "user_found": False},
                source_ip=source_ip,
                status="failure",
            )

            return None, False

    def reset_password(
        self,
        db: Session,
        token: str,
        new_password: str,
        source_ip: str = None,
    ) -> tuple[bool, str]:
        """
        Reset user password with a valid reset token.

        Args:
            db: Database session
            token: Password reset token
            new_password: New password (will be hashed by AuthService)
            source_ip: IP address of reset request

        Returns:
            Tuple of (success, message)
        """
        # Verify token
        email = self.verify_reset_token(token)
        if not email:
            return False, "Invalid or expired reset token"

        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False, "User not found"

        # Import here to avoid circular imports
        from app.services.auth_service import AuthService

        # Hash and update password
        try:
            user = AuthService.update_user(
                db,
                str(user.id),
                password=new_password
            )

            # Audit log: password reset successful
            audit_logger.log_event(
                event_type=AuditEventType.USER_PASSWORD_CHANGED,
                actor_id=str(user.id),
                resource_id=str(user.id),
                resource_type="user",
                action="update",
                severity=AuditEventSeverity.INFO,
                details={"email": email, "method": "password_reset"},
                source_ip=source_ip,
                status="success",
            )

            return True, "Password reset successfully"
        except Exception as e:
            # Audit log: password reset failed
            audit_logger.log_event(
                event_type=AuditEventType.USER_PASSWORD_RESET,
                actor_id=str(user.id),
                resource_id=str(user.id),
                resource_type="user",
                action="update",
                severity=AuditEventSeverity.WARNING,
                details={"email": email, "error": str(e)},
                source_ip=source_ip,
                status="failure",
            )

            return False, f"Failed to reset password: {str(e)}"


class PasswordResetEmailService(EmailVerificationService):
    """Service for generating password reset emails"""

    def generate_reset_email_body(self, username: str, reset_url: str) -> tuple[str, str]:
        """
        Generate email subject and body for password reset.

        Args:
            username: User's username
            reset_url: Full URL with password reset token

        Returns:
            Tuple of (subject, body)
        """
        subject = "Reset your HyperFactory password"

        body = f"""
Dear {username},

We received a request to reset the password for your HyperFactory account.
Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email or contact
support if you believe your account has been compromised.

Best regards,
HyperFactory Team
"""

        return subject, body

    def generate_reset_email_html(self, username: str, reset_url: str) -> str:
        """
        Generate HTML email for password reset.

        Args:
            username: User's username
            reset_url: Full URL with password reset token

        Returns:
            HTML email body
        """
        return f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto;">
        <h2>Reset Your Password</h2>

        <p>Dear {username},</p>

        <p>We received a request to reset the password for your HyperFactory account.
        Click the button below to reset your password:</p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background-color: #4CAF50; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Reset Password
            </a>
        </p>

        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all; color: #666; font-size: 12px;">{reset_url}</p>

        <p style="color: #999; font-size: 12px;">
            This link will expire in 1 hour.
        </p>

        <p style="margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px;">
            If you didn't request a password reset, please ignore this email or
            <a href="https://app.example.com/support" style="color: #4CAF50;">contact support</a>
            if you believe your account has been compromised.
        </p>

        <p style="margin-top: 30px; color: #999;">
            Best regards,<br/>
            HyperFactory Team
        </p>
    </div>
</body>
</html>
"""


# Global password reset manager instance
password_reset_manager = PasswordResetManager(
    secret_key=PASSWORD_RESET_SECRET_KEY,
    expiration_hours=PASSWORD_RESET_TOKEN_EXPIRATION_HOURS,
)
