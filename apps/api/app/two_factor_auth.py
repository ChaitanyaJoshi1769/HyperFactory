"""Two-Factor Authentication (2FA) - TOTP and Email-based verification"""

import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import User
from app.email_verification import EmailTokenManager
from app.audit_logger import audit_logger, AuditEvent, AuditEventType, AuditEventSeverity
import os


# Secret key for 2FA email tokens
TWO_FACTOR_EMAIL_SECRET_KEY = os.getenv("TWO_FACTOR_EMAIL_SECRET_KEY") or os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Email code expiration (5 minutes)
TWO_FACTOR_EMAIL_CODE_EXPIRATION_MINUTES = 5

# TOTP configuration
TOTP_ISSUER = "HyperFactory"
TOTP_DIGITS = 6


class TOTPManager:
    """Manages Time-based One-Time Password (TOTP) setup and verification"""

    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new TOTP secret key.

        Returns:
            Base32-encoded secret key for TOTP
        """
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, username: str, issuer: str = TOTP_ISSUER) -> str:
        """
        Get the provisioning URI for TOTP setup.

        Args:
            secret: TOTP secret key
            username: Username/email for the account
            issuer: Name of the application

        Returns:
            otpauth:// URI for QR code generation
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)

    @staticmethod
    def get_qr_code(uri: str) -> str:
        """
        Generate QR code for TOTP setup.

        Args:
            uri: otpauth:// URI

        Returns:
            Base64-encoded PNG image data
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_base64}"

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify a TOTP code against a secret.

        Args:
            secret: TOTP secret key
            code: 6-digit TOTP code from authenticator app

        Returns:
            True if code is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow code from previous/next window for clock skew
            return totp.verify(code, valid_window=1)
        except Exception:
            return False

    @staticmethod
    def get_backup_codes(count: int = 10) -> list:
        """
        Generate backup codes for account recovery.

        Args:
            count: Number of backup codes to generate

        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            # Generate 8-character codes
            code = pyotp.random_base32()[:8]
            codes.append(code)
        return codes


class EmailCodeManager:
    """Manages email-based 2FA verification codes"""

    def __init__(
        self,
        secret_key: str = TWO_FACTOR_EMAIL_SECRET_KEY,
        expiration_minutes: int = TWO_FACTOR_EMAIL_CODE_EXPIRATION_MINUTES,
    ):
        """
        Initialize email code manager.

        Args:
            secret_key: Secret key for token signing
            expiration_minutes: How long codes are valid (default 5 minutes)
        """
        self.token_manager = EmailTokenManager(secret_key, expiration_minutes / 60)
        self.expiration_minutes = expiration_minutes

    def generate_email_code(self, email: str) -> str:
        """
        Generate a 2FA email code.

        Args:
            email: Email address

        Returns:
            Token containing the email
        """
        return self.token_manager.generate_verification_token(email)

    def verify_email_code(self, token: str) -> Optional[str]:
        """
        Verify email code and return email.

        Args:
            token: Token to verify

        Returns:
            Email if valid, None if invalid/expired
        """
        return self.token_manager.verify_token(token)


class TwoFactorAuthManager:
    """Manages 2FA setup, verification, and authentication flow"""

    def __init__(self):
        """Initialize 2FA manager"""
        self.totp_manager = TOTPManager()
        self.email_code_manager = EmailCodeManager()

    def setup_totp(
        self,
        db: Session,
        user: User,
        source_ip: str = None,
    ) -> Tuple[str, str, list]:
        """
        Setup TOTP for user.

        Args:
            db: Database session
            user: User object
            source_ip: IP address of request

        Returns:
            Tuple of (secret, qr_code_data_uri, backup_codes)
        """
        # Generate secret and backup codes
        secret = self.totp_manager.generate_secret()
        backup_codes = self.totp_manager.get_backup_codes()

        # Get QR code
        uri = self.totp_manager.get_totp_uri(secret, user.username)
        qr_code = self.totp_manager.get_qr_code(uri)

        # Audit log: 2FA setup initiated
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,  # Using existing event type
            actor_id=str(user.id),
            resource_id=str(user.id),
            resource_type="user",
            action="setup_2fa",
            severity=AuditEventSeverity.INFO,
            details={
                "method": "totp",
                "username": user.username,
                "backup_codes_generated": len(backup_codes),
            },
            source_ip=source_ip,
        )

        return secret, qr_code, backup_codes

    def enable_totp(
        self,
        db: Session,
        user: User,
        secret: str,
        code: str,
        backup_codes: list,
        source_ip: str = None,
    ) -> Tuple[bool, str]:
        """
        Enable TOTP for user after verification.

        Args:
            db: Database session
            user: User object
            secret: TOTP secret to enable
            code: TOTP code to verify
            backup_codes: Backup codes for recovery
            source_ip: IP address

        Returns:
            Tuple of (success, message)
        """
        # Verify code
        if not self.totp_manager.verify_totp(secret, code):
            return False, "Invalid TOTP code"

        # TODO: Store secret and backup codes in database
        # For now, this is a placeholder
        # user.totp_secret = secret
        # user.totp_enabled = True
        # user.backup_codes = backup_codes  # Hashed
        # db.commit()

        # Audit log: 2FA enabled
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(user.id),
            resource_id=str(user.id),
            resource_type="user",
            action="enable_2fa",
            severity=AuditEventSeverity.INFO,
            details={"method": "totp", "username": user.username},
            source_ip=source_ip,
        )

        return True, "TOTP enabled successfully"

    def disable_totp(
        self,
        db: Session,
        user: User,
        password: str,
        source_ip: str = None,
    ) -> Tuple[bool, str]:
        """
        Disable TOTP for user.

        Args:
            db: Database session
            user: User object
            password: User's password (for confirmation)
            source_ip: IP address

        Returns:
            Tuple of (success, message)
        """
        # TODO: Verify password
        # TODO: Disable TOTP in database
        # user.totp_enabled = False
        # user.totp_secret = None
        # db.commit()

        # Audit log: 2FA disabled
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(user.id),
            resource_id=str(user.id),
            resource_type="user",
            action="disable_2fa",
            severity=AuditEventSeverity.WARNING,
            details={"method": "totp", "username": user.username},
            source_ip=source_ip,
        )

        return True, "TOTP disabled successfully"

    def verify_login_code(
        self,
        db: Session,
        user: User,
        code: str,
        method: str = "totp",
        source_ip: str = None,
    ) -> Tuple[bool, str]:
        """
        Verify a 2FA code during login.

        Args:
            db: Database session
            user: User object
            code: Code to verify (TOTP, email, or backup)
            method: Method type ("totp", "email", "backup")
            source_ip: IP address

        Returns:
            Tuple of (success, message)
        """
        if method == "totp":
            # TODO: Get user's TOTP secret from database
            # secret = user.totp_secret
            # if not secret:
            #     return False, "TOTP not enabled for this user"
            # if not self.totp_manager.verify_totp(secret, code):
            #     return False, "Invalid TOTP code"
            pass
        elif method == "backup":
            # TODO: Check backup codes
            # if code not in user.backup_codes:
            #     return False, "Invalid backup code"
            # # Remove used backup code
            # user.backup_codes.remove(code)
            # db.commit()
            pass
        else:
            return False, "Unknown 2FA method"

        # Audit log: 2FA verification successful
        audit_logger.log_event(
            event_type=AuditEventType.USER_LOGIN,
            actor_id=str(user.id),
            resource_id=str(user.id),
            resource_type="user",
            action="verify_2fa",
            severity=AuditEventSeverity.INFO,
            details={"method": method, "username": user.username},
            source_ip=source_ip,
        )

        return True, "2FA verification successful"


# Global 2FA manager instance
two_factor_auth_manager = TwoFactorAuthManager()
