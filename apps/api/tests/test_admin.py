"""Admin management endpoint tests"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate


def create_admin_user(client: TestClient, db: Session):
    """Helper to create an admin user and get token"""
    user_data = UserCreate(
        username="admin_user",
        email="admin@example.com",
        password="AdminPassword123!",
    )
    user = AuthService.create_user(db, user_data)
    user.is_admin = True
    db.commit()

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "admin_user",
            "password": "AdminPassword123!",
        }
    )
    token = login_response.json()["access_token"]
    return user, token


def create_regular_user(db: Session, username="user1", email="user1@example.com"):
    """Helper to create a regular user"""
    user_data = UserCreate(
        username=username,
        email=email,
        password="UserPassword123!",
    )
    return AuthService.create_user(db, user_data)


# ============================================================================
# User Management Tests
# ============================================================================

def test_list_users_as_admin(client: TestClient, db: Session):
    """Test listing users as admin"""
    admin_user, admin_token = create_admin_user(client, db)

    # Create some users
    for i in range(5):
        create_regular_user(db, f"user{i}", f"user{i}@example.com")

    # List users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 5  # At least the 5 created users


def test_list_users_with_pagination(client: TestClient, db: Session):
    """Test user listing with pagination"""
    admin_user, admin_token = create_admin_user(client, db)

    # Create multiple users
    for i in range(10):
        create_regular_user(db, f"user{i}", f"user{i}@example.com")

    # Get first page
    response = client.get(
        "/api/admin/users?skip=0&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) <= 5


def test_list_users_not_admin(client: TestClient, db: Session):
    """Test listing users fails for non-admin"""
    # Create regular user and login
    user_data = UserCreate(
        username="regular_user",
        email="regular@example.com",
        password="RegularPassword123!",
    )
    AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "regular_user",
            "password": "RegularPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Try to list users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_get_user_by_id(client: TestClient, db: Session):
    """Test getting user by ID"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    response = client.get(
        f"/api/admin/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["username"] == user.username


def test_get_nonexistent_user(client: TestClient, db: Session):
    """Test getting non-existent user returns 404"""
    admin_user, admin_token = create_admin_user(client, db)
    fake_id = uuid4()

    response = client.get(
        f"/api/admin/users/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


# ============================================================================
# Admin Status Tests
# ============================================================================

def test_set_admin_status(client: TestClient, db: Session):
    """Test setting admin status"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    response = client.patch(
        f"/api/admin/users/{user.id}/admin?is_admin=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] == True


def test_revoke_own_admin_status(client: TestClient, db: Session):
    """Test that admin cannot remove their own admin status"""
    admin_user, admin_token = create_admin_user(client, db)

    response = client.patch(
        f"/api/admin/users/{admin_user.id}/admin?is_admin=false",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Cannot remove admin status from yourself" in response.json()["detail"]


# ============================================================================
# User Role Tests
# ============================================================================

def test_set_user_role(client: TestClient, db: Session):
    """Test setting user role"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    response = client.patch(
        f"/api/admin/users/{user.id}/role?role=engineer",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "engineer"


def test_set_invalid_role(client: TestClient, db: Session):
    """Test setting invalid role fails"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    response = client.patch(
        f"/api/admin/users/{user.id}/role?role=invalid_role",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400


# ============================================================================
# User Activation Tests
# ============================================================================

def test_activate_user(client: TestClient, db: Session):
    """Test activating a user"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    # Deactivate first
    AuthService.deactivate_user(db, user.id)

    # Activate
    response = client.patch(
        f"/api/admin/users/{user.id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == True


def test_deactivate_user(client: TestClient, db: Session):
    """Test deactivating a user"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    response = client.patch(
        f"/api/admin/users/{user.id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == False


def test_deactivate_self(client: TestClient, db: Session):
    """Test that admin cannot deactivate themselves"""
    admin_user, admin_token = create_admin_user(client, db)

    response = client.patch(
        f"/api/admin/users/{admin_user.id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Cannot deactivate yourself" in response.json()["detail"]


# ============================================================================
# User Deletion Tests
# ============================================================================

def test_delete_user(client: TestClient, db: Session):
    """Test deleting a user"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)
    user_id = user.id

    response = client.delete(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

    # Verify user is deleted
    deleted_user = AuthService.get_user(db, user_id)
    assert deleted_user is None


def test_delete_self(client: TestClient, db: Session):
    """Test that admin cannot delete themselves"""
    admin_user, admin_token = create_admin_user(client, db)

    response = client.delete(
        f"/api/admin/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Cannot delete yourself" in response.json()["detail"]


def test_delete_user_with_api_keys(client: TestClient, db: Session):
    """Test deleting user also deletes their API keys"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    # Create API key for user
    api_key, key_value = AuthService.create_api_key(db, user.id, "Test Key")

    # Delete user
    response = client.delete(
        f"/api/admin/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

    # Verify API key no longer works
    response = client.get(
        "/api/auth/me",
        headers={"X-API-Key": key_value}
    )
    assert response.status_code == 401


# ============================================================================
# API Key Management Tests
# ============================================================================

def test_list_user_api_keys_as_admin(client: TestClient, db: Session):
    """Test admin can list user's API keys"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    # Create API keys for user
    for i in range(3):
        AuthService.create_api_key(db, user.id, f"Key {i}")

    response = client.get(
        f"/api/admin/users/{user.id}/api-keys",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) == 3


def test_delete_user_api_key_as_admin(client: TestClient, db: Session):
    """Test admin can delete user's API key"""
    admin_user, admin_token = create_admin_user(client, db)
    user = create_regular_user(db)

    # Create API key
    api_key, _ = AuthService.create_api_key(db, user.id, "Test Key")

    response = client.delete(
        f"/api/admin/users/{user.id}/api-keys/{api_key.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


# ============================================================================
# System Statistics Tests
# ============================================================================

def test_get_system_stats(client: TestClient, db: Session):
    """Test getting system statistics"""
    admin_user, admin_token = create_admin_user(client, db)

    # Create some users
    for i in range(3):
        create_regular_user(db, f"user{i}", f"user{i}@example.com")

    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "timestamp" in data
    assert "users" in data
    assert "hardware" in data
    assert "supply_chain" in data
    assert "manufacturing" in data
    assert "design" in data

    # Verify counts
    assert data["users"]["total"] >= 4  # admin + 3 regular users
    assert data["users"]["admins"] >= 1


def test_stats_not_admin(client: TestClient, db: Session):
    """Test that non-admin cannot get stats"""
    # Create regular user
    user_data = UserCreate(
        username="regular_user",
        email="regular@example.com",
        password="RegularPassword123!",
    )
    AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "regular_user",
            "password": "RegularPassword123!",
        }
    )
    token = login_response.json()["access_token"]

    # Try to get stats
    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


# ============================================================================
# User Search Tests
# ============================================================================

def test_search_users_by_username(client: TestClient, db: Session):
    """Test searching users by username"""
    admin_user, admin_token = create_admin_user(client, db)

    # Create users
    create_regular_user(db, "john_doe", "john@example.com")
    create_regular_user(db, "john_smith", "john_smith@example.com")
    create_regular_user(db, "jane_doe", "jane@example.com")

    response = client.get(
        "/api/admin/users/search?query=john&field=username",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2
    assert all("john" in user["username"].lower() for user in users)


def test_search_users_by_email(client: TestClient, db: Session):
    """Test searching users by email"""
    admin_user, admin_token = create_admin_user(client, db)

    create_regular_user(db, "user1", "john@example.com")
    create_regular_user(db, "user2", "jane@example.com")

    response = client.get(
        "/api/admin/users/search?query=example&field=email",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2


def test_search_users_by_organization(client: TestClient, db: Session):
    """Test searching users by organization"""
    admin_user, admin_token = create_admin_user(client, db)

    # Create users with organizations
    user_data = UserCreate(
        username="acme_user",
        email="acme@example.com",
        password="Password123!",
        organization="ACME Corp"
    )
    AuthService.create_user(db, user_data)

    response = client.get(
        "/api/admin/users/search?query=ACME&field=organization",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    assert any("ACME" in (user.get("organization") or "") for user in users)


def test_search_invalid_field(client: TestClient, db: Session):
    """Test search with invalid field returns error"""
    admin_user, admin_token = create_admin_user(client, db)

    response = client.get(
        "/api/admin/users/search?query=test&field=invalid_field",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
