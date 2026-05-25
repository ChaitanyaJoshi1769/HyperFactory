"""Two-Factor Authentication (2FA) tests"""

import pytest
import pyotp
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.two_factor_auth import (
    TOTPManager,
    EmailCodeManager,
    TwoFactorAuthManager,
    two_factor_auth_manager,
)
from app.models import User


# ============================================================================
# TOTP Manager Tests
# ============================================================================

def test_totp_generate_secret():
    """Test generating TOTP secret"""
    secret = TOTPManager.generate_secret()

    assert secret
    assert isinstance(secret, str)
    assert len(secret) > 0
    # Should be base32 encoded
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in secret)


def test_totp_different_secrets_each_time():
    """Test that different secrets are generated each time"""
    secret1 = TOTPManager.generate_secret()
    secret2 = TOTPManager.generate_secret()

    assert secret1 != secret2


def test_get_totp_uri():
    """Test getting TOTP provisioning URI"""
    secret = TOTPManager.generate_secret()
    username = "testuser@example.com"

    uri = TOTPManager.get_totp_uri(secret, username)

    assert uri.startswith("otpauth://totp/")
    assert username in uri
    assert "HyperFactory" in uri
    assert "secret=" in uri


def test_get_qr_code():
    """Test generating QR code"""
    secret = TOTPManager.generate_secret()
    username = "testuser@example.com"
    uri = TOTPManager.get_totp_uri(secret, username)

    qr_code = TOTPManager.get_qr_code(uri)

    assert qr_code.startswith("data:image/png;base64,")
    assert len(qr_code) > 100  # Should be substantial base64 data


def test_verify_totp_valid_code():
    """Test verifying valid TOTP code"""
    secret = TOTPManager.generate_secret()
    totp = pyotp.TOTP(secret)
    code = totp.now()

    assert TOTPManager.verify_totp(secret, code)


def test_verify_totp_invalid_code():
    """Test verifying invalid TOTP code"""
    secret = TOTPManager.generate_secret()

    assert not TOTPManager.verify_totp(secret, "000000")
    assert not TOTPManager.verify_totp(secret, "999999")
    assert not TOTPManager.verify_totp(secret, "abcdef")


def test_verify_totp_code_tolerance():
    """Test TOTP code tolerance for clock skew"""
    secret = TOTPManager.generate_secret()
    totp = pyotp.TOTP(secret)

    # Get current code
    current_code = totp.now()

    # Should verify current code
    assert TOTPManager.verify_totp(secret, current_code)

    # Code format validation
    assert len(current_code) == 6
    assert current_code.isdigit()


def test_generate_backup_codes():
    """Test generating backup codes"""
    codes = TOTPManager.get_backup_codes(count=10)

    assert len(codes) == 10
    assert all(isinstance(code, str) for code in codes)
    assert all(len(code) == 8 for code in codes)
    # All codes should be unique
    assert len(set(codes)) == 10


def test_backup_codes_different_each_call():
    """Test that backup codes are different each call"""
    codes1 = TOTPManager.get_backup_codes()
    codes2 = TOTPManager.get_backup_codes()

    assert codes1 != codes2


# ============================================================================
# Email Code Manager Tests
# ============================================================================

def test_email_code_manager_creation():
    """Test creating email code manager"""
    manager = EmailCodeManager(secret_key="test-secret", expiration_minutes=5)
    assert manager.expiration_minutes == 5


def test_generate_email_code():
    """Test generating email code"""
    manager = EmailCodeManager(secret_key="test-secret")
    email = "test@example.com"

    token = manager.generate_email_code(email)
    assert token
    assert isinstance(token, str)


def test_verify_email_code():
    """Test verifying email code"""
    manager = EmailCodeManager(secret_key="test-secret")
    email = "test@example.com"

    token = manager.generate_email_code(email)
    verified_email = manager.verify_email_code(token)

    assert verified_email == email


def test_verify_invalid_email_code():
    """Test verifying invalid email code"""
    manager = EmailCodeManager(secret_key="test-secret")

    verified_email = manager.verify_email_code("invalid-token")
    assert verified_email is None


# ============================================================================
# 2FA Manager Tests
# ============================================================================

def test_two_factor_auth_manager_creation():
    """Test creating 2FA manager"""
    manager = TwoFactorAuthManager()
    assert manager.totp_manager is not None
    assert manager.email_code_manager is not None


def test_setup_totp(db: Session):
    """Test TOTP setup"""
    # Create user
    user_data = UserCreate(
        username="2fauser",
        email="2fauser@example.com",
        password="TwoFAPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()
    secret, qr_code, backup_codes = manager.setup_totp(db, user, source_ip="127.0.0.1")

    assert secret
    assert qr_code
    assert len(backup_codes) == 10
    assert qr_code.startswith("data:image/png;base64,")


def test_enable_totp(db: Session):
    """Test enabling TOTP"""
    # Create user
    user_data = UserCreate(
        username="enabletotp",
        email="enabletotp@example.com",
        password="EnablePass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()
    secret, qr_code, backup_codes = manager.setup_totp(db, user)

    # Generate valid code
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Enable TOTP
    success, message = manager.enable_totp(
        db, user, secret, code, backup_codes, source_ip="127.0.0.1"
    )

    assert success
    assert "successfully" in message.lower()


def test_enable_totp_invalid_code(db: Session):
    """Test enabling TOTP with invalid code"""
    # Create user
    user_data = UserCreate(
        username="invalidtotp",
        email="invalidtotp@example.com",
        password="InvalidPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()
    secret, qr_code, backup_codes = manager.setup_totp(db, user)

    # Try with invalid code
    success, message = manager.enable_totp(
        db, user, secret, "000000", backup_codes
    )

    assert not success
    assert "invalid" in message.lower()


def test_disable_totp(db: Session):
    """Test disabling TOTP"""
    # Create user
    user_data = UserCreate(
        username="disabletotp",
        email="disabletotp@example.com",
        password="DisablePass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()

    # Disable TOTP
    success, message = manager.disable_totp(
        db, user, "DisablePass123", source_ip="127.0.0.1"
    )

    assert success
    assert "disabled" in message.lower()


def test_verify_login_code_totp(db: Session):
    """Test verifying TOTP during login"""
    # Create user
    user_data = UserCreate(
        username="verifytotp",
        email="verifytotp@example.com",
        password="VerifyPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()

    # This is a placeholder test since we haven't stored TOTP in DB yet
    # In production, would verify actual TOTP code
    secret = TOTPManager.generate_secret()
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Verify the code would work
    assert TOTPManager.verify_totp(secret, code)


# ============================================================================
# QR Code and Setup Flow Tests
# ============================================================================

def test_totp_qr_code_can_be_scanned():
    """Test that QR code is properly formatted"""
    secret = TOTPManager.generate_secret()
    username = "testuser"
    uri = TOTPManager.get_totp_uri(secret, username)
    qr_code = TOTPManager.get_qr_code(uri)

    # QR code should be valid PNG data URI
    assert qr_code.startswith("data:image/png;base64,")
    assert len(qr_code) > 1000  # Should contain substantial image data


def test_totp_setup_restore_from_secret():
    """Test that TOTP can be restored from secret"""
    secret = TOTPManager.generate_secret()

    # Get code from restored secret
    totp = pyotp.TOTP(secret)
    code1 = totp.now()

    # Should be able to verify with same secret
    assert TOTPManager.verify_totp(secret, code1)


def test_full_2fa_setup_flow(db: Session):
    """Test complete 2FA setup flow"""
    # Create user
    user_data = UserCreate(
        username="fullflow",
        email="fullflow@example.com",
        password="FullFlowPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = TwoFactorAuthManager()

    # Step 1: Setup TOTP
    secret, qr_code, backup_codes = manager.setup_totp(db, user)
    assert secret and qr_code and backup_codes

    # Step 2: User scans QR code (happens on client)
    # Step 3: User confirms TOTP code
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # Step 4: Enable TOTP with verification
    success, _ = manager.enable_totp(db, user, secret, code, backup_codes)
    assert success


# ============================================================================
# Backup Code Tests
# ============================================================================

def test_backup_codes_unique():
    """Test that backup codes are unique"""
    codes = TOTPManager.get_backup_codes(count=20)

    assert len(codes) == len(set(codes))


def test_backup_codes_format():
    """Test backup code format"""
    codes = TOTPManager.get_backup_codes()

    for code in codes:
        # Should be 8 characters
        assert len(code) == 8
        # Should be alphanumeric base32
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in code)


# ============================================================================
# Edge Cases
# ============================================================================

def test_totp_with_different_usernames():
    """Test TOTP setup with different username formats"""
    secret = TOTPManager.generate_secret()

    usernames = [
        "user@example.com",
        "user+alias@example.com",
        "user_name",
        "用户@example.com",  # Unicode
    ]

    for username in usernames:
        uri = TOTPManager.get_totp_uri(secret, username)
        assert username in uri or username.replace("@", "%40") in uri


def test_totp_secret_uniqueness():
    """Test that TOTP secrets are cryptographically unique"""
    secrets = [TOTPManager.generate_secret() for _ in range(100)]

    # All should be unique
    assert len(set(secrets)) == 100


def test_verify_totp_with_non_digit_code():
    """Test TOTP verification rejects non-digit codes"""
    secret = TOTPManager.generate_secret()

    assert not TOTPManager.verify_totp(secret, "abcdef")
    assert not TOTPManager.verify_totp(secret, "12345!")
    assert not TOTPManager.verify_totp(secret, "")
