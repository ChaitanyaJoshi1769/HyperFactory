"""Rate limiting tests"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import time

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.rate_limiter import (
    RateLimiter,
    login_limiter,
    register_limiter,
    check_rate_limit,
)


def create_authenticated_user(client: TestClient, db: Session, username: str = "testuser", email: str = "test@example.com"):
    """Helper to create and authenticate a user"""
    user_data = UserCreate(
        username=username,
        email=email,
        password="TestPass123",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "TestPass123",
        }
    )
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return user, token
    return user, None


# ============================================================================
# Rate Limiter Unit Tests
# ============================================================================

def test_rate_limiter_creation():
    """Test creating a rate limiter"""
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    assert limiter.max_attempts == 3
    assert limiter.window_seconds == 60


def test_rate_limiter_allows_first_attempt():
    """Test that first attempt is always allowed"""
    limiter = RateLimiter(max_attempts=1, window_seconds=60)
    assert limiter.is_allowed("user1")


def test_rate_limiter_blocks_after_max_attempts():
    """Test that requests are blocked after max attempts"""
    limiter = RateLimiter(max_attempts=2, window_seconds=60)
    identifier = "user1"

    # First two attempts should be allowed
    assert limiter.is_allowed(identifier)
    limiter.add_attempt(identifier)

    assert limiter.is_allowed(identifier)
    limiter.add_attempt(identifier)

    # Third attempt should be blocked
    assert not limiter.is_allowed(identifier)


def test_rate_limiter_resets_after_window():
    """Test that rate limit resets after time window"""
    limiter = RateLimiter(max_attempts=1, window_seconds=1)
    identifier = "user1"

    # First attempt allowed
    assert limiter.is_allowed(identifier)
    limiter.add_attempt(identifier)

    # Immediately blocked
    assert not limiter.is_allowed(identifier)

    # Wait for window to expire
    time.sleep(1.1)

    # Should be allowed again
    assert limiter.is_allowed(identifier)


def test_rate_limiter_get_remaining_attempts():
    """Test getting remaining attempts"""
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    identifier = "user1"

    assert limiter.get_remaining_attempts(identifier) == 3

    limiter.add_attempt(identifier)
    assert limiter.get_remaining_attempts(identifier) == 2

    limiter.add_attempt(identifier)
    assert limiter.get_remaining_attempts(identifier) == 1

    limiter.add_attempt(identifier)
    assert limiter.get_remaining_attempts(identifier) == 0


def test_rate_limiter_multiple_identifiers():
    """Test that different identifiers have separate limits"""
    limiter = RateLimiter(max_attempts=1, window_seconds=60)

    # First identifier
    assert limiter.is_allowed("user1")
    limiter.add_attempt("user1")
    assert not limiter.is_allowed("user1")

    # Second identifier should still be allowed
    assert limiter.is_allowed("user2")
    limiter.add_attempt("user2")
    assert not limiter.is_allowed("user2")


# ============================================================================
# Login Rate Limiting Tests
# ============================================================================

def test_login_rate_limiting(client: TestClient, db: Session):
    """Test login rate limiting"""
    # Create a user first
    user_data = UserCreate(
        username="ratelimituser",
        email="ratelimit@example.com",
        password="TestPass123",
    )
    AuthService.create_user(db, user_data)

    # Make 5 successful login attempts
    for i in range(5):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "ratelimituser",
                "password": "TestPass123",
            }
        )
        assert response.status_code == 200

    # 6th attempt should be rate limited
    response = client.post(
        "/api/auth/login",
        json={
            "username": "ratelimituser",
            "password": "TestPass123",
        }
    )
    assert response.status_code == 429
    assert "Too many attempts" in response.json()["detail"]


def test_login_rate_limiting_includes_retry_after_header(client: TestClient, db: Session):
    """Test that rate limiting response includes Retry-After header"""
    user_data = UserCreate(
        username="rateuserheader",
        email="rateheader@example.com",
        password="TestPass123",
    )
    AuthService.create_user(db, user_data)

    # Make max attempts
    for i in range(5):
        client.post(
            "/api/auth/login",
            json={
                "username": "rateuserheader",
                "password": "TestPass123",
            }
        )

    # Next attempt should include Retry-After header
    response = client.post(
        "/api/auth/login",
        json={
            "username": "rateuserheader",
            "password": "TestPass123",
        }
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_login_rate_limiting_per_username(client: TestClient, db: Session):
    """Test that login rate limiting is per username"""
    # Create two users
    user1_data = UserCreate(
        username="user1",
        email="user1@example.com",
        password="TestPass123",
    )
    user2_data = UserCreate(
        username="user2",
        email="user2@example.com",
        password="TestPass123",
    )
    AuthService.create_user(db, user1_data)
    AuthService.create_user(db, user2_data)

    # Rate limit user1
    for i in range(5):
        client.post(
            "/api/auth/login",
            json={"username": "user1", "password": "TestPass123"}
        )

    # User1 should be rate limited
    response = client.post(
        "/api/auth/login",
        json={"username": "user1", "password": "TestPass123"}
    )
    assert response.status_code == 429

    # User2 should still work
    response = client.post(
        "/api/auth/login",
        json={"username": "user2", "password": "TestPass123"}
    )
    assert response.status_code == 200


# ============================================================================
# Registration Rate Limiting Tests
# ============================================================================

def test_register_rate_limiting(client: TestClient, db: Session):
    """Test registration rate limiting"""
    # Make 3 registration attempts from same email
    email = "ratelimitreg@example.com"

    for i in range(3):
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"reguser{i}",
                "email": email,
                "password": "TestPass123",
            }
        )
        # First one succeeds, next ones fail due to duplicate email but still count
        assert response.status_code in [201, 409]

    # 4th attempt should be rate limited
    response = client.post(
        "/api/auth/register",
        json={
            "username": "reguser4",
            "email": email,
            "password": "TestPass123",
        }
    )
    assert response.status_code == 429


def test_register_rate_limiting_per_email(client: TestClient, db: Session):
    """Test that register rate limiting is per email"""
    # Rate limit one email
    email1 = "email1@example.com"
    for i in range(3):
        client.post(
            "/api/auth/register",
            json={
                "username": f"user1_{i}",
                "email": email1,
                "password": "TestPass123",
            }
        )

    # Different email should still work
    email2 = "email2@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "username": "user2",
            "email": email2,
            "password": "TestPass123",
        }
    )
    assert response.status_code == 201


# ============================================================================
# Rate Limit Reset Tests
# ============================================================================

def test_rate_limiter_reset_time(client: TestClient, db: Session):
    """Test getting reset time from rate limiter"""
    limiter = RateLimiter(max_attempts=1, window_seconds=60)
    identifier = "user1"

    # No attempts yet - reset time should be now
    reset_time = limiter.get_reset_time(identifier)
    assert reset_time is not None

    # After adding attempt - reset time should be in future
    limiter.add_attempt(identifier)
    reset_time = limiter.get_reset_time(identifier)
    assert reset_time is not None


# ============================================================================
# Edge Cases
# ============================================================================

def test_rate_limiter_zero_window(client: TestClient, db: Session):
    """Test rate limiter with very small window"""
    limiter = RateLimiter(max_attempts=1, window_seconds=0)
    identifier = "user1"

    # Immediate first attempt
    assert limiter.is_allowed(identifier)
    limiter.add_attempt(identifier)

    # Wait a tiny bit and try again
    time.sleep(0.01)

    # Should fail (window is 0)
    assert not limiter.is_allowed(identifier)


def test_rate_limiter_cleanup(client: TestClient, db: Session):
    """Test that rate limiter cleans up old attempts"""
    limiter = RateLimiter(max_attempts=2, window_seconds=1)
    identifier = "cleanup_user"

    # Add two attempts
    limiter.add_attempt(identifier)
    limiter.add_attempt(identifier)

    # Should be at limit
    assert not limiter.is_allowed(identifier)

    # Wait for window to expire
    time.sleep(1.1)

    # Cleanup should remove old attempts
    limiter._cleanup_old_attempts(identifier)

    # Should be allowed again
    assert limiter.is_allowed(identifier)
