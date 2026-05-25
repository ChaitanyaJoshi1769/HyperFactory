"""Authentication endpoint and service tests"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.main import app
from app.db import get_db, Base, engine
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate, UserLogin
from app.models.user import User, APIKey
from tests.conftest import override_get_db, test_db


# ============================================================================
# User Registration Tests
# ============================================================================

def test_register_new_user(client: TestClient, db: Session):
    """Test successful user registration"""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "organization": "Test Org"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["organization"] == "Test Org"
    assert data["is_active"] == True
    assert data["is_admin"] == False
    assert data["role"] == "user"
    assert "id" in data
    assert "created_at" in data


def test_register_duplicate_username(client: TestClient, db: Session):
    """Test registration fails with duplicate username"""
    # Create first user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "password": "TestPassword123!",
        }
    )

    # Try to create duplicate
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "password": "TestPassword123!",
        }
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_duplicate_email(client: TestClient, db: Session):
    """Test registration fails with duplicate email"""
    # Create first user
    client.post(
        "/api/auth/register",
        json={
            "username": "user1",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    # Try to create duplicate
    response = client.post(
        "/api/auth/register",
        json={
            "username": "user2",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )
    assert response.status_code == 409


def test_register_short_password(client: TestClient, db: Session):
    """Test registration fails with password too short"""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",  # Less than 8 chars
        }
    )
    assert response.status_code == 422  # Validation error


# ============================================================================
# User Login Tests
# ============================================================================

def test_login_success(client: TestClient, db: Session):
    """Test successful login"""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert isinstance(data["expires_in"], int)


def test_login_invalid_username(client: TestClient, db: Session):
    """Test login fails with invalid username"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": "nonexistent",
            "password": "SomePassword123!",
        }
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_invalid_password(client: TestClient, db: Session):
    """Test login fails with invalid password"""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "CorrectPassword123!",
        }
    )

    # Try with wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "WrongPassword123!",
        }
    )
    assert response.status_code == 401


def test_login_inactive_user(client: TestClient, db: Session):
    """Test login fails for inactive user"""
    # Create user
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )
    user = AuthService.create_user(db, user_data)

    # Deactivate user
    AuthService.deactivate_user(db, user.id)

    # Try to login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    assert response.status_code == 401


# ============================================================================
# Get Current User Tests
# ============================================================================

def test_get_current_user(client: TestClient, db: Session):
    """Test getting current user with valid token"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting current user fails with invalid token"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_get_current_user_no_token(client: TestClient):
    """Test getting current user fails without token"""
    response = client.get("/api/auth/me")
    assert response.status_code == 403


# ============================================================================
# Update User Profile Tests
# ============================================================================

def test_update_user_profile(client: TestClient, db: Session):
    """Test updating user profile"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Update profile
    response = client.put(
        "/api/auth/me",
        json={
            "full_name": "Updated Name",
            "organization": "New Org",
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["organization"] == "New Org"


def test_update_user_password(client: TestClient, db: Session):
    """Test updating user password"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "OldPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "OldPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Update password
    response = client.put(
        "/api/auth/me",
        json={
            "password": "NewPassword123!",
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    # Old password should fail
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "OldPassword123!",
        }
    )
    assert login_response.status_code == 401

    # New password should work
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "NewPassword123!",
        }
    )
    assert login_response.status_code == 200


# ============================================================================
# API Key Tests
# ============================================================================

def test_create_api_key(client: TestClient, db: Session):
    """Test creating an API key"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Create API key
    response = client.post(
        "/api/auth/api-keys",
        json={
            "name": "Test Key",
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Key"
    assert "key" in data
    assert "id" in data
    assert "created_at" in data
    assert "message" in data


def test_list_api_keys(client: TestClient, db: Session):
    """Test listing user's API keys"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Create multiple keys
    for i in range(3):
        client.post(
            "/api/auth/api-keys",
            json={"name": f"Key {i+1}"},
            headers={"Authorization": f"Bearer {token}"}
        )

    # List keys
    response = client.get(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("id" in key and "name" in key and "is_active" in key for key in data)


def test_revoke_api_key(client: TestClient, db: Session):
    """Test revoking an API key"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Create key
    create_response = client.post(
        "/api/auth/api-keys",
        json={"name": "Test Key"},
        headers={"Authorization": f"Bearer {token}"}
    )
    key_id = create_response.json()["id"]

    # Revoke key
    revoke_response = client.post(
        f"/api/auth/api-keys/{key_id}/revoke",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert revoke_response.status_code == 204

    # Verify key is inactive
    list_response = client.get(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    keys = list_response.json()
    assert len(keys) == 1
    assert keys[0]["is_active"] == False


def test_delete_api_key(client: TestClient, db: Session):
    """Test deleting an API key"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Create key
    create_response = client.post(
        "/api/auth/api-keys",
        json={"name": "Test Key"},
        headers={"Authorization": f"Bearer {token}"}
    )
    key_id = create_response.json()["id"]

    # Delete key
    delete_response = client.delete(
        f"/api/auth/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 204

    # Verify key is deleted
    list_response = client.get(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    keys = list_response.json()
    assert len(keys) == 0


# ============================================================================
# API Key Authentication Tests
# ============================================================================

def test_api_key_authentication(client: TestClient, db: Session):
    """Test authenticating with API key"""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Create API key
    create_response = client.post(
        "/api/auth/api-keys",
        json={"name": "Test Key"},
        headers={"Authorization": f"Bearer {token}"}
    )
    api_key = create_response.json()["key"]

    # Use API key to access protected endpoint
    response = client.get(
        "/api/auth/me",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


def test_invalid_api_key(client: TestClient):
    """Test authentication fails with invalid API key"""
    response = client.get(
        "/api/auth/me",
        headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 401


# ============================================================================
# Token Expiration Tests
# ============================================================================

def test_expired_token(client: TestClient, db: Session):
    """Test that expired tokens are rejected"""
    # Create user with expired token
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )
    user = AuthService.create_user(db, user_data)

    # Create token that's already expired
    from app.security import create_access_token
    expired_token = create_access_token(
        {"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(seconds=-1)  # Negative = already expired
    )

    # Try to use expired token
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


# ============================================================================
# Auth Service Tests
# ============================================================================

def test_auth_service_create_user(db: Session):
    """Test AuthService.create_user()"""
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
        full_name="Test User",
    )
    user = AuthService.create_user(db, user_data)

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active == True
    assert user.is_admin == False
    assert user.role == "user"
    assert user.hashed_password != "TestPassword123!"  # Should be hashed


def test_auth_service_authenticate_user(db: Session):
    """Test AuthService.authenticate_user()"""
    # Create user
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )
    AuthService.create_user(db, user_data)

    # Authenticate with correct password
    login_data = UserLogin(username="testuser", password="TestPassword123!")
    user = AuthService.authenticate_user(db, login_data)
    assert user is not None
    assert user.username == "testuser"

    # Authenticate with incorrect password
    bad_login = UserLogin(username="testuser", password="WrongPassword")
    user = AuthService.authenticate_user(db, bad_login)
    assert user is None


def test_auth_service_api_key_lifecycle(db: Session):
    """Test API key creation, verification, revocation, and deletion"""
    # Create user
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
    )
    user = AuthService.create_user(db, user_data)

    # Create API key
    api_key_record, key_value = AuthService.create_api_key(
        db,
        user.id,
        "Test Key"
    )
    assert api_key_record.is_active == True
    assert api_key_record.key_hash != key_value  # Should be hashed

    # Verify API key works
    verified_user_id = AuthService.verify_api_key(db, key_value)
    assert verified_user_id == user.id

    # Revoke API key
    AuthService.revoke_api_key(db, api_key_record.id)
    verified_user_id = AuthService.verify_api_key(db, key_value)
    assert verified_user_id is None

    # Create new key and delete it
    api_key_record2, key_value2 = AuthService.create_api_key(
        db,
        user.id,
        "Another Key"
    )
    AuthService.delete_api_key(db, api_key_record2.id)

    # Verify deleted key doesn't work
    verified_user_id = AuthService.verify_api_key(db, key_value2)
    assert verified_user_id is None


def test_auth_service_update_user(db: Session):
    """Test AuthService.update_user()"""
    # Create user
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="OldPassword123!",
    )
    user = AuthService.create_user(db, user_data)

    # Update user
    updated = AuthService.update_user(
        db,
        user.id,
        full_name="New Name",
        organization="New Org",
        password="NewPassword123!"
    )

    assert updated.full_name == "New Name"
    assert updated.organization == "New Org"

    # Verify old password doesn't work
    login_data = UserLogin(username="testuser", password="OldPassword123!")
    auth_user = AuthService.authenticate_user(db, login_data)
    assert auth_user is None

    # Verify new password works
    login_data = UserLogin(username="testuser", password="NewPassword123!")
    auth_user = AuthService.authenticate_user(db, login_data)
    assert auth_user is not None
