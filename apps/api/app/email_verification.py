"""Email verification token generation and validation"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from itsdangerous import TimedSerializer, BadSignature, SignatureExpired
import os

# Secret key for signing tokens - should be from environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Token expiration time (default 24 hours)
TOKEN_EXPIRATION_HOURS = 24


class EmailTokenManager:
    """Manages email verification tokens"""

    def __init__(self, secret_key: str = SECRET_KEY, expiration_hours: int = TOKEN_EXPIRATION_HOURS):
        """
        Initialize email token manager.

        Args:
            secret_key: Secret key for token signing
            expiration_hours: How long tokens are valid (default 24 hours)
        """
        self.serializer = TimedSerializer(secret_key)
        self.expiration_hours = expiration_hours

    def generate_verification_token(self, email: str) -> str:
        """
        Generate an email verification token.

        Args:
            email: Email address to verify

        Returns:
            Signed verification token
        """
        return self.serializer.dumps(email)

    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify an email token and return the email address.

        Args:
            token: Token to verify

        Returns:
            Email address if valid, None if invalid or expired
        """
        try:
            email = self.serializer.loads(
                token,
                max_age=self.expiration_hours * 3600  # Convert to seconds
            )
            return email
        except (BadSignature, SignatureExpired):
            return None

    def is_token_valid(self, token: str) -> bool:
        """
        Check if a token is valid without extracting the email.

        Args:
            token: Token to check

        Returns:
            True if valid, False otherwise
        """
        return self.verify_token(token) is not None


# Global email token manager instance
email_token_manager = EmailTokenManager(secret_key=SECRET_KEY, expiration_hours=TOKEN_EXPIRATION_HOURS)


class EmailVerificationService:
    """Service for managing email verification workflow"""

    def __init__(self, token_manager: EmailTokenManager = None):
        """
        Initialize email verification service.

        Args:
            token_manager: EmailTokenManager instance (uses global if not provided)
        """
        self.token_manager = token_manager or email_token_manager

    def generate_verification_email_body(self, username: str, verification_url: str) -> Tuple[str, str]:
        """
        Generate email subject and body for verification.

        Args:
            username: User's username
            verification_url: Full URL with verification token

        Returns:
            Tuple of (subject, body)
        """
        subject = "Verify your HyperFactory email address"

        body = f"""
Dear {username},

Thank you for registering with HyperFactory! To complete your account setup,
please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
HyperFactory Team
"""

        return subject, body

    def generate_verification_email_html(self, username: str, verification_url: str) -> str:
        """
        Generate HTML email for verification.

        Args:
            username: User's username
            verification_url: Full URL with verification token

        Returns:
            HTML email body
        """
        return f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto;">
        <h2>Welcome to HyperFactory!</h2>

        <p>Dear {username},</p>

        <p>Thank you for registering with HyperFactory! To complete your account setup,
        please verify your email address by clicking the button below:</p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}"
               style="background-color: #4CAF50; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 4px; display: inline-block;">
                Verify Email Address
            </a>
        </p>

        <p>Or copy and paste this link in your browser:</p>
        <p style="word-break: break-all; color: #666;">{verification_url}</p>

        <p style="color: #999; font-size: 12px;">This link will expire in 24 hours.</p>

        <p style="margin-top: 30px;">
            If you didn't create this account, please ignore this email.
        </p>

        <p style="margin-top: 30px; color: #999;">
            Best regards,<br/>
            HyperFactory Team
        </p>
    </div>
</body>
</html>
"""


# Placeholder for email sending functionality
# In production, this would integrate with SendGrid, AWS SES, etc.

def send_verification_email(email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send a verification email.

    Args:
        email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: HTML email body (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    # TODO: Implement actual email sending
    # This is a placeholder that logs the email
    import logging

    logger = logging.getLogger("hyperfactory.email")
    logger.info(f"Would send email to {email}: {subject}")

    # In production, integrate with email service:
    # - SendGrid API
    # - AWS SES
    # - Mailgun
    # - Postmark
    # - etc.

    return True
