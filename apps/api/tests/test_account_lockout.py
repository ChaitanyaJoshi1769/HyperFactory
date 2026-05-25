"""Account lockout tests"""

import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.account_lockout import account_lockout_manager, AccountLockoutManager
from app.models import User


# ============================================================================
# Account Lockout Manager Unit Tests
# ============================================================================

def test_account_lockout_manager_creation():
    """Test creating an account lockout manager"""
    manager = AccountLockoutManager(max_failed_attempts=3, lockout_duration_minutes=15)
    assert manager.max_failed_attempts == 3
    assert manager.lockout_duration_minutes == 15


def test_account_lock_and_unlock(db: Session):
    """Test locking and unlocking an account"""
    # Create test user
    user_data = UserCreate(
        username="locktest",
        email="locktest@example.com",
        password="LockTestPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = AccountLockoutManager()

    # Account should not be locked initially
    assert not account_lockout_manager.is_account_locked(db, str(user.id))

    # Lock the account
    manager.lock_account(db, user, source_ip="127.0.0.1")

    # Account should now be locked
    assert account_lockout_manager.is_account_locked(db, str(user.id))

    # Unlock the account
    manager.unlock_account(db, str(user.id))

    # Account should be unlocked
    assert not account_lockout_manager.is_account_locked(db, str(user.id))


def test_account_auto_unlock_after_timeout(db: Session):
    """Test automatic account unlock after timeout"""
    # Create test user
    user_data = UserCreate(
        username="autounlocktest",
        email="autounlock@example.com",
        password="AutoUnlockPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Create manager with very short timeout
    manager = AccountLockoutManager(max_failed_attempts=5, lockout_duration_minutes=0)

    # Lock the account
    manager.lock_account(db, user, source_ip="127.0.0.1")
    assert account_lockout_manager.is_account_locked(db, str(user.id))

    # Manually set locked_until to past time to simulate timeout
    user.locked_until = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    # Account should auto-unlock
    assert not account_lockout_manager.is_account_locked(db, str(user.id))


def test_get_lockout_status_unlocked(db: Session):
    """Test getting lockout status for unlocked account"""
    # Create test user
    user_data = UserCreate(
        username="statustest",
        email="statustest@example.com",
        password="StatusTestPass123",
    )
    user = AuthService.create_user(db, user_data)

    status = account_lockout_manager.get_lockout_status(db, str(user.id))
    assert not status["locked"]


def test_get_lockout_status_locked(db: Session):
    """Test getting lockout status for locked account"""
    # Create test user
    user_data = UserCreate(
        username="lockedstatustest",
        email="lockedstatus@example.com",
        password="LockedStatusPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Lock the account
    account_lockout_manager.lock_account(db, user, source_ip="127.0.0.1")

    # Get status
    status = account_lockout_manager.get_lockout_status(db, str(user.id))
    assert status["locked"]
    assert "locked_until" in status
    assert "seconds_remaining" in status
    assert status["seconds_remaining"] > 0


def test_record_failed_login_before_threshold(db: Session):
    """Test recording failed login before threshold"""
    # Create test user
    user_data = UserCreate(
        username="failtest1",
        email="failtest1@example.com",
        password="FailTest1Pass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = AccountLockoutManager(max_failed_attempts=5)

    # Record first failed attempt (should not lock)
    locked = manager.record_failed_login(db, user, failed_attempts=1, source_ip="127.0.0.1")
    assert not locked
    assert not account_lockout_manager.is_account_locked(db, str(user.id))


def test_record_failed_login_at_threshold(db: Session):
    """Test recording failed login at threshold"""
    # Create test user
    user_data = UserCreate(
        username="failtest2",
        email="failtest2@example.com",
        password="FailTest2Pass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = AccountLockoutManager(max_failed_attempts=5)

    # Record 5th failed attempt (should lock)
    locked = manager.record_failed_login(db, user, failed_attempts=5, source_ip="127.0.0.1")
    assert locked
    assert account_lockout_manager.is_account_locked(db, str(user.id))


# ============================================================================
# Login Endpoint Account Lockout Tests
# ============================================================================

def test_login_attempt_on_locked_account(client: TestClient, db: Session):
    """Test that login attempts on locked account are rejected"""
    # Create and authenticate user
    user_data = UserCreate(
        username="lockendpointtest",
        email="lockendpointtest@example.com",
        password="LockEndpointPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Lock the account
    account_lockout_manager.lock_account(db, user, source_ip="127.0.0.1")

    # Try to login
    response = client.post(
        "/api/auth/login",
        json={"username": "lockendpointtest", "password": "LockEndpointPass123"}
    )

    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()


def test_account_lockout_after_failed_logins(client: TestClient, db: Session):
    """Test that account locks after repeated failed login attempts"""
    # Create user
    user_data = UserCreate(
        username="faillocktestuser",
        email="faildlocktest@example.com",
        password="FailLockPass123",
    )
    AuthService.create_user(db, user_data)

    # Make 5 failed login attempts
    for i in range(5):
        response = client.post(
            "/api/auth/login",
            json={"username": "faillocktestuser", "password": "WrongPassword"}
        )
        assert response.status_code == 401

    # 6th attempt should be locked out (403, not 401)
    response = client.post(
        "/api/auth/login",
        json={"username": "faillocktestuser", "password": "WrongPassword"}
    )
    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()


def test_successful_login_after_lockout_expires(client: TestClient, db: Session):
    """Test that successful login works after lockout expires"""
    # Create user
    user_data = UserCreate(
        username="lockexpiretest",
        email="lockexpiretest@example.com",
        password="LockExpirePass123",
    )
    user = AuthService.create_user(db, user_data)

    # Lock the account with immediate expiration
    manager = AccountLockoutManager(max_failed_attempts=5, lockout_duration_minutes=0)
    manager.lock_account(db, user, source_ip="127.0.0.1")

    # Manually set lock to expire immediately
    user.locked_until = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    # Should be able to login now (after auto-unlock)
    response = client.post(
        "/api/auth/login",
        json={"username": "lockexpiretest", "password": "LockExpirePass123"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


# ============================================================================
# Audit Logging Tests for Account Lockout
# ============================================================================

def test_account_lockout_audit_log(client: TestClient, db: Session):
    """Test that account lockout is logged to audit log"""
    import json
    import os

    # Clear audit log
    log_file = "logs/audit.log"
    if os.path.exists(log_file):
        open(log_file, 'w').close()

    # Create user
    user_data = UserCreate(
        username="auditlocktest",
        email="auditlocktest@example.com",
        password="AuditLockPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Lock the account
    account_lockout_manager.lock_account(
        db, user, source_ip="127.0.0.1", reason="test_lockout"
    )

    # Read audit log
    events = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    try:
                        event = json.loads(parts[3].strip())
                        if event.get("event_type") == "security:account_lockout":
                            events.append(event)
                    except json.JSONDecodeError:
                        pass

    # Verify lockout was logged
    assert len(events) > 0
    event = events[-1]
    assert event["event_type"] == "security:account_lockout"
    assert event["severity"] == "critical"
    assert event["action"] == "lock"


def test_login_failed_on_locked_account_audit_log(client: TestClient, db: Session):
    """Test that login failures on locked accounts are logged"""
    import json
    import os

    # Clear audit log
    log_file = "logs/audit.log"
    if os.path.exists(log_file):
        open(log_file, 'w').close()

    # Create and lock user
    user_data = UserCreate(
        username="auditfaillock",
        email="auditfaillock@example.com",
        password="AuditFailLockPass123",
    )
    user = AuthService.create_user(db, user_data)
    account_lockout_manager.lock_account(db, user, source_ip="127.0.0.1")

    # Try to login
    response = client.post(
        "/api/auth/login",
        json={"username": "auditfaillock", "password": "AuditFailLockPass123"}
    )
    assert response.status_code == 403

    # Read audit log
    events = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    try:
                        event = json.loads(parts[3].strip())
                        if event.get("event_type") == "user:login_failed":
                            events.append(event)
                    except json.JSONDecodeError:
                        pass

    # Verify failure was logged
    assert len(events) > 0
    # Find the one with "account_locked" reason
    locked_events = [e for e in events if e.get("details", {}).get("reason") == "account_locked"]
    assert len(locked_events) > 0


# ============================================================================
# Edge Cases
# ============================================================================

def test_lockout_nonexistent_user(db: Session):
    """Test lockout behavior for nonexistent user"""
    manager = AccountLockoutManager()

    # Should not error
    is_locked = manager.is_account_locked(db, "00000000-0000-0000-0000-000000000000")
    assert not is_locked

    status = manager.get_lockout_status(db, "00000000-0000-0000-0000-000000000000")
    assert not status["locked"]


def test_multiple_lockout_unlock_cycles(db: Session):
    """Test multiple lockout/unlock cycles"""
    # Create test user
    user_data = UserCreate(
        username="cycletest",
        email="cycletest@example.com",
        password="CycleTestPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = AccountLockoutManager()

    # Cycle through lock/unlock multiple times
    for i in range(3):
        assert not account_lockout_manager.is_account_locked(db, str(user.id))

        manager.lock_account(db, user, source_ip="127.0.0.1")
        assert account_lockout_manager.is_account_locked(db, str(user.id))

        manager.unlock_account(db, str(user.id))
        assert not account_lockout_manager.is_account_locked(db, str(user.id))


def test_lockout_status_time_precision(db: Session):
    """Test that lockout status reports accurate remaining time"""
    # Create test user
    user_data = UserCreate(
        username="timetest",
        email="timetest@example.com",
        password="TimeTestPass123",
    )
    user = AuthService.create_user(db, user_data)

    # Create manager with specific lockout duration
    manager = AccountLockoutManager(lockout_duration_minutes=10)
    manager.lock_account(db, user, source_ip="127.0.0.1")

    # Get status
    status = account_lockout_manager.get_lockout_status(db, str(user.id))

    # Remaining time should be close to 600 seconds (10 minutes)
    remaining = status["seconds_remaining"]
    assert 590 <= remaining <= 610  # Allow for execution time
