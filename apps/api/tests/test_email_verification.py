"""Email verification tests"""

import pytest
import time
from itsdangerous import TimedSerializer, SignatureExpired, BadSignature
from app.email_verification import (
    EmailTokenManager,
    EmailVerificationService,
    email_token_manager,
)


# ============================================================================
# Email Token Manager Tests
# ============================================================================

def test_email_token_manager_creation():
    """Test creating an email token manager"""
    manager = EmailTokenManager(secret_key="test-secret", expiration_hours=24)
    assert manager.expiration_hours == 24


def test_generate_verification_token():
    """Test generating a verification token"""
    manager = EmailTokenManager(secret_key="test-secret")
    email = "test@example.com"

    token = manager.generate_verification_token(email)
    assert token
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_valid_token():
    """Test verifying a valid token"""
    manager = EmailTokenManager(secret_key="test-secret")
    email = "test@example.com"

    token = manager.generate_verification_token(email)
    verified_email = manager.verify_token(token)

    assert verified_email == email


def test_verify_invalid_token():
    """Test verifying an invalid token"""
    manager = EmailTokenManager(secret_key="test-secret")

    # Invalid token
    verified_email = manager.verify_token("invalid-token-xyz")
    assert verified_email is None


def test_verify_wrong_secret_key():
    """Test that token generated with one key can't be verified with another"""
    manager1 = EmailTokenManager(secret_key="secret1")
    manager2 = EmailTokenManager(secret_key="secret2")

    email = "test@example.com"
    token = manager1.generate_verification_token(email)

    # Should not verify with different secret
    verified_email = manager2.verify_token(token)
    assert verified_email is None


def test_verify_expired_token():
    """Test that expired tokens are rejected"""
    # Create manager with very short expiration
    manager = EmailTokenManager(secret_key="test-secret", expiration_hours=0)
    email = "test@example.com"

    token = manager.generate_verification_token(email)

    # Wait a tiny bit to ensure expiration
    time.sleep(0.1)

    # Token should be expired
    verified_email = manager.verify_token(token)
    assert verified_email is None


def test_is_token_valid_valid_token():
    """Test is_token_valid with valid token"""
    manager = EmailTokenManager(secret_key="test-secret")
    email = "test@example.com"

    token = manager.generate_verification_token(email)
    assert manager.is_token_valid(token)


def test_is_token_valid_invalid_token():
    """Test is_token_valid with invalid token"""
    manager = EmailTokenManager(secret_key="test-secret")

    assert not manager.is_token_valid("invalid-token")


def test_token_contains_email():
    """Test that token can be decoded multiple times"""
    manager = EmailTokenManager(secret_key="test-secret")
    email = "verify@example.com"

    token = manager.generate_verification_token(email)

    # Verify token multiple times
    for _ in range(3):
        verified_email = manager.verify_token(token)
        assert verified_email == email


def test_different_emails_produce_different_tokens():
    """Test that different emails produce different tokens"""
    manager = EmailTokenManager(secret_key="test-secret")

    token1 = manager.generate_verification_token("user1@example.com")
    token2 = manager.generate_verification_token("user2@example.com")

    assert token1 != token2


# ============================================================================
# Email Verification Service Tests
# ============================================================================

def test_email_verification_service_creation():
    """Test creating an email verification service"""
    service = EmailVerificationService()
    assert service.token_manager is not None


def test_email_verification_service_custom_manager():
    """Test creating service with custom token manager"""
    custom_manager = EmailTokenManager(secret_key="custom-secret")
    service = EmailVerificationService(token_manager=custom_manager)

    assert service.token_manager == custom_manager


def test_generate_verification_email_body():
    """Test generating verification email body"""
    service = EmailVerificationService()

    username = "testuser"
    url = "https://example.com/verify?token=abc123"

    subject, body = service.generate_verification_email_body(username, url)

    assert subject == "Verify your HyperFactory email address"
    assert "testuser" in body
    assert "https://example.com/verify?token=abc123" in body
    assert "24 hours" in body


def test_generate_verification_email_html():
    """Test generating HTML verification email"""
    service = EmailVerificationService()

    username = "htmluser"
    url = "https://example.com/verify?token=xyz789"

    html = service.generate_verification_email_html(username, url)

    assert "htmluser" in html
    assert "https://example.com/verify?token=xyz789" in html
    assert "<html>" in html
    assert "Welcome to HyperFactory" in html
    assert "Verify Email Address" in html


def test_verification_email_contains_necessary_elements():
    """Test that verification email contains all necessary elements"""
    service = EmailVerificationService()

    subject, body = service.generate_verification_email_body(
        "john",
        "https://app.example.com/verify?token=token123"
    )

    # Check subject
    assert subject  # Non-empty
    assert "verify" in subject.lower()

    # Check body contains
    assert "john" in body
    assert "token123" in body
    assert "register" in body.lower() or "account" in body.lower()
    assert "24 hours" in body or "24" in body


# ============================================================================
# Integration Tests
# ============================================================================

def test_email_verification_workflow():
    """Test complete email verification workflow"""
    manager = EmailTokenManager(secret_key="test-secret")
    service = EmailVerificationService(token_manager=manager)

    # User registers
    email = "newuser@example.com"
    token = manager.generate_verification_token(email)

    # Email sent (simulated)
    subject, body = service.generate_verification_email_body(
        "newuser",
        f"https://app.example.com/verify?token={token}"
    )

    assert "newuser" in body
    assert token in body

    # User clicks link and verifies
    verified_email = manager.verify_token(token)
    assert verified_email == email


def test_multiple_verification_tokens():
    """Test generating multiple tokens for different users"""
    manager = EmailTokenManager(secret_key="test-secret")

    users = [
        ("alice@example.com", "alice"),
        ("bob@example.com", "bob"),
        ("charlie@example.com", "charlie"),
    ]

    tokens = {}
    for email, username in users:
        token = manager.generate_verification_token(email)
        tokens[email] = token

    # Verify all tokens work correctly
    for email, token in tokens.items():
        verified_email = manager.verify_token(token)
        assert verified_email == email


# ============================================================================
# Global Instance Tests
# ============================================================================

def test_global_email_token_manager():
    """Test that global email token manager works"""
    email = "global@example.com"

    token = email_token_manager.generate_verification_token(email)
    assert token

    verified_email = email_token_manager.verify_token(token)
    assert verified_email == email


# ============================================================================
# Edge Cases
# ============================================================================

def test_token_with_special_characters_in_email():
    """Test token generation with special characters in email"""
    manager = EmailTokenManager(secret_key="test-secret")

    email = "user+tag@example.co.uk"
    token = manager.generate_verification_token(email)
    verified_email = manager.verify_token(token)

    assert verified_email == email


def test_empty_secret_key_still_works():
    """Test that empty secret key works (though not recommended)"""
    manager = EmailTokenManager(secret_key="")
    email = "test@example.com"

    token = manager.generate_verification_token(email)
    verified_email = manager.verify_token(token)

    assert verified_email == email


def test_very_long_email():
    """Test token with very long email address"""
    manager = EmailTokenManager(secret_key="test-secret")

    email = "a" * 100 + "@example.com"
    token = manager.generate_verification_token(email)
    verified_email = manager.verify_token(token)

    assert verified_email == email


def test_unicode_in_email():
    """Test token with unicode characters"""
    manager = EmailTokenManager(secret_key="test-secret")

    email = "用户@example.com"  # Chinese characters
    token = manager.generate_verification_token(email)
    verified_email = manager.verify_token(token)

    assert verified_email == email


def test_token_format_is_url_safe():
    """Test that generated tokens can be used in URLs"""
    manager = EmailTokenManager(secret_key="test-secret")

    email = "url@example.com"
    token = manager.generate_verification_token(email)

    # Token should only contain URL-safe characters
    import re
    assert re.match(r"^[A-Za-z0-9._-]+$", token) or "=" in token  # Base64 can have =
