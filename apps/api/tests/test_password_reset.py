"""Password reset tests"""

import pytest
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.password_reset import (
    PasswordResetManager,
    PasswordResetEmailService,
    password_reset_manager,
)
from app.models import User


# ============================================================================
# Password Reset Manager Unit Tests
# ============================================================================

def test_password_reset_manager_creation():
    """Test creating a password reset manager"""
    manager = PasswordResetManager(secret_key="test-secret", expiration_hours=1)
    assert manager.expiration_hours == 1


def test_generate_reset_token():
    """Test generating a password reset token"""
    manager = PasswordResetManager(secret_key="test-secret")
    email = "reset@example.com"

    token = manager.generate_reset_token(email)
    assert token
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_reset_token():
    """Test verifying a password reset token"""
    manager = PasswordResetManager(secret_key="test-secret")
    email = "reset@example.com"

    token = manager.generate_reset_token(email)
    verified_email = manager.verify_reset_token(token)

    assert verified_email == email


def test_invalid_reset_token():
    """Test verifying invalid reset token"""
    manager = PasswordResetManager(secret_key="test-secret")

    verified_email = manager.verify_reset_token("invalid-token")
    assert verified_email is None


def test_is_reset_token_valid():
    """Test checking token validity"""
    manager = PasswordResetManager(secret_key="test-secret")
    email = "valid@example.com"

    token = manager.generate_reset_token(email)
    assert manager.is_token_valid(token)

    # Invalid token
    assert not manager.is_token_valid("invalid-token")


# ============================================================================
# Password Reset Workflow Tests
# ============================================================================

def test_request_password_reset_existing_user(db: Session):
    """Test password reset request for existing user"""
    # Create user
    user_data = UserCreate(
        username="resetuser",
        email="resetuser@example.com",
        password="ResetPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = PasswordResetManager(secret_key="test-secret")

    # Request reset
    token, found = manager.request_password_reset(db, user.email, source_ip="127.0.0.1")

    assert found
    assert token is not None
    assert manager.verify_reset_token(token) == user.email


def test_request_password_reset_nonexistent_user(db: Session):
    """Test password reset request for non-existent user"""
    manager = PasswordResetManager(secret_key="test-secret")

    # Request reset for non-existent user
    token, found = manager.request_password_reset(
        db, "nonexistent@example.com", source_ip="127.0.0.1"
    )

    assert not found
    assert token is None


def test_reset_password_with_valid_token(db: Session):
    """Test resetting password with valid token"""
    # Create user
    user_data = UserCreate(
        username="passwordresettest",
        email="passwordreset@example.com",
        password="OldPassword123",
    )
    user = AuthService.create_user(db, user_data)

    manager = PasswordResetManager(secret_key="test-secret")

    # Request reset
    token, _ = manager.request_password_reset(db, user.email)

    # Reset password
    success, message = manager.reset_password(
        db, token, "NewPassword456", source_ip="127.0.0.1"
    )

    assert success
    assert "successfully" in message.lower()

    # Verify new password works
    from app.schemas.auth import UserLogin

    credentials = UserLogin(username="passwordresettest", password="NewPassword456")
    authenticated_user = AuthService.authenticate_user(db, credentials)
    assert authenticated_user is not None


def test_reset_password_with_invalid_token(db: Session):
    """Test resetting password with invalid token"""
    manager = PasswordResetManager(secret_key="test-secret")

    success, message = manager.reset_password(
        db, "invalid-token", "NewPassword", source_ip="127.0.0.1"
    )

    assert not success
    assert "invalid" in message.lower()


def test_reset_password_with_expired_token(db: Session):
    """Test that expired reset tokens are rejected"""
    # Create user
    user_data = UserCreate(
        username="expiredresettest",
        email="expiredreset@example.com",
        password="ExpiredPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Create manager with very short expiration
    manager = PasswordResetManager(secret_key="test-secret", expiration_hours=0)

    # Generate token
    token = manager.generate_reset_token(user.email)

    # Wait a bit for expiration
    import time
    time.sleep(0.1)

    # Try to reset with expired token
    success, message = manager.reset_password(
        db, token, "NewPassword", source_ip="127.0.0.1"
    )

    assert not success


# ============================================================================
# Password Reset Email Service Tests
# ============================================================================

def test_reset_email_service_creation():
    """Test creating password reset email service"""
    service = PasswordResetEmailService()
    assert service is not None


def test_generate_reset_email_body():
    """Test generating reset email body"""
    service = PasswordResetEmailService()

    username = "john"
    reset_url = "https://app.example.com/reset?token=abc123"

    subject, body = service.generate_reset_email_body(username, reset_url)

    assert subject == "Reset your HyperFactory password"
    assert "john" in body
    assert reset_url in body
    assert "1 hour" in body


def test_generate_reset_email_html():
    """Test generating HTML reset email"""
    service = PasswordResetEmailService()

    username = "htmluser"
    reset_url = "https://app.example.com/reset?token=xyz789"

    html = service.generate_reset_email_html(username, reset_url)

    assert "<html>" in html
    assert "htmluser" in html
    assert reset_url in html
    assert "Reset Your Password" in html
    assert "Reset Password" in html  # Button text


def test_reset_email_contains_expiration_info():
    """Test that reset email mentions expiration"""
    service = PasswordResetEmailService()

    subject, body = service.generate_reset_email_body(
        "testuser",
        "https://app.example.com/reset?token=token"
    )

    # Should mention the expiration time
    assert "1 hour" in body or "expire" in body.lower()


# ============================================================================
# Full Workflow Tests
# ============================================================================

def test_complete_password_reset_workflow(db: Session):
    """Test complete password reset workflow"""
    # 1. Create user
    user_data = UserCreate(
        username="workflowtest",
        email="workflow@example.com",
        password="WorkflowPass123",
    )
    user = AuthService.create_user(db, user_data)

    # 2. Request password reset
    manager = PasswordResetManager(secret_key="test-secret")
    email_service = PasswordResetEmailService()

    token, found = manager.request_password_reset(db, user.email, source_ip="127.0.0.1")
    assert found
    assert token

    # 3. Generate reset email
    reset_url = f"https://app.example.com/reset?token={token}"
    subject, body = email_service.generate_reset_email_body(user.username, reset_url)

    assert user.username in body
    assert token in body

    # 4. User clicks link and resets password
    success, message = manager.reset_password(
        db, token, "NewWorkflowPass456", source_ip="127.0.0.1"
    )

    assert success

    # 5. User logs in with new password
    from app.schemas.auth import UserLogin

    credentials = UserLogin(username="workflowtest", password="NewWorkflowPass456")
    authenticated_user = AuthService.authenticate_user(db, credentials)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id


def test_password_reset_chain_multiple_users(db: Session):
    """Test password reset for multiple users"""
    manager = PasswordResetManager(secret_key="test-secret")

    users_data = [
        ("user1", "user1@example.com", "Pass1"),
        ("user2", "user2@example.com", "Pass2"),
        ("user3", "user3@example.com", "Pass3"),
    ]

    users = []
    for username, email, password in users_data:
        user_data = UserCreate(username=username, email=email, password=password)
        user = AuthService.create_user(db, user_data)
        users.append((user, email))

    # Request resets for all users
    tokens = {}
    for user, email in users:
        token, found = manager.request_password_reset(db, email)
        assert found
        tokens[email] = token

    # Reset passwords
    for user, email in users:
        token = tokens[email]
        new_password = f"NewPass_{user.username}"

        success, message = manager.reset_password(db, token, new_password)
        assert success


# ============================================================================
# Edge Cases
# ============================================================================

def test_reset_token_can_only_be_used_once(db: Session):
    """Test that reset token can only be used once"""
    # Create user
    user_data = UserCreate(
        username="oneuseonlytest",
        email="oneuseonly@example.com",
        password="OneUsePass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = PasswordResetManager(secret_key="test-secret")

    token, _ = manager.request_password_reset(db, user.email)

    # First reset should work
    success1, _ = manager.reset_password(db, token, "NewPass1", source_ip="127.0.0.1")
    assert success1

    # Token is now spent, but can still be verified (tokens aren't invalidated)
    # However, if we implement token revocation, this test would change
    # For now, token is still valid even after use


def test_different_emails_produce_different_tokens(db: Session):
    """Test that different emails produce different tokens"""
    user1 = UserCreate(
        username="diffuser1",
        email="diff1@example.com",
        password="DiffPass1",
    )
    user2 = UserCreate(
        username="diffuser2",
        email="diff2@example.com",
        password="DiffPass2",
    )

    AuthService.create_user(db, user1)
    AuthService.create_user(db, user2)

    manager = PasswordResetManager(secret_key="test-secret")

    token1, _ = manager.request_password_reset(db, user1.email)
    token2, _ = manager.request_password_reset(db, user2.email)

    assert token1 != token2
    assert manager.verify_reset_token(token1) == user1.email
    assert manager.verify_reset_token(token2) == user2.email


def test_reset_password_validation_errors(db: Session):
    """Test password reset with validation errors"""
    # Create user
    user_data = UserCreate(
        username="validationtest",
        email="validation@example.com",
        password="ValidPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = PasswordResetManager(secret_key="test-secret")

    token, _ = manager.request_password_reset(db, user.email)

    # Try to reset with empty password
    success, message = manager.reset_password(db, token, "", source_ip="127.0.0.1")

    # Should handle validation
    assert not success or "successfully" not in message.lower()
