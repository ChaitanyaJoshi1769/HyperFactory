"""Audit logging tests"""

import pytest
import json
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.audit_logger import audit_logger, AuditEventType, AuditEventSeverity, AuditEvent


def read_audit_log() -> list:
    """Read and parse audit log file"""
    log_file = "logs/audit.log"
    if not os.path.exists(log_file):
        return []

    events = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Parse the log line to extract the JSON part
                # Format: "timestamp - name - level - json_message"
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    try:
                        json_str = parts[3].strip()
                        event = json.loads(json_str)
                        events.append(event)
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass

    return events


def clear_audit_log():
    """Clear the audit log file"""
    log_file = "logs/audit.log"
    if os.path.exists(log_file):
        open(log_file, 'w').close()


# ============================================================================
# Audit Event Tests
# ============================================================================

def test_audit_event_creation():
    """Test creating an audit event"""
    event = AuditEvent(
        event_type=AuditEventType.USER_REGISTERED,
        actor_id="user1",
        resource_id="user1",
        resource_type="user",
        action="create",
        severity=AuditEventSeverity.INFO,
        details={"username": "testuser", "email": "test@example.com"},
        source_ip="127.0.0.1",
    )

    assert event.event_type == AuditEventType.USER_REGISTERED
    assert event.actor_id == "user1"
    assert event.resource_id == "user1"
    assert event.resource_type == "user"
    assert event.action == "create"
    assert event.severity == AuditEventSeverity.INFO


def test_audit_event_to_dict():
    """Test converting audit event to dictionary"""
    event = AuditEvent(
        event_type=AuditEventType.USER_LOGIN,
        actor_id="user1",
        resource_id="user1",
        resource_type="user",
        action="login",
        severity=AuditEventSeverity.INFO,
        source_ip="127.0.0.1",
    )

    event_dict = event.to_dict()
    assert event_dict["event_type"] == "user:login"
    assert event_dict["actor_id"] == "user1"
    assert event_dict["severity"] == "info"
    assert event_dict["status"] == "success"


def test_audit_event_to_json():
    """Test converting audit event to JSON"""
    event = AuditEvent(
        event_type=AuditEventType.USER_LOGIN_FAILED,
        resource_type="user",
        action="login",
        severity=AuditEventSeverity.WARNING,
        details={"username": "testuser", "reason": "invalid_credentials"},
        source_ip="127.0.0.1",
        status="failure",
    )

    json_str = event.to_json()
    assert json_str
    assert "user:login_failed" in json_str
    assert "warning" in json_str
    assert "invalid_credentials" in json_str


# ============================================================================
# Audit Logger Tests
# ============================================================================

def test_audit_logger_initialization():
    """Test that audit logger initializes correctly"""
    logger = audit_logger
    assert logger is not None
    assert logger.logger.name == "hyperfactory.audit"


# ============================================================================
# Authentication Audit Logging Tests
# ============================================================================

def test_user_registration_audit_log(client: TestClient, db: Session):
    """Test that user registration is logged"""
    clear_audit_log()

    user_data = UserCreate(
        username="audituser",
        email="audit@example.com",
        password="AuditPass123",
    )

    response = client.post(
        "/api/auth/register",
        json={
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,
        }
    )

    assert response.status_code == 201
    created_user = response.json()

    # Check audit log
    events = read_audit_log()
    user_registered_events = [e for e in events if e.get("event_type") == "user:registered"]

    assert len(user_registered_events) > 0
    event = user_registered_events[-1]
    assert event["event_type"] == "user:registered"
    assert event["resource_type"] == "user"
    assert event["action"] == "create"
    assert event["severity"] == "info"
    assert event["details"]["username"] == "audituser"
    assert event["details"]["email"] == "audit@example.com"


def test_user_login_success_audit_log(client: TestClient, db: Session):
    """Test that successful login is logged"""
    clear_audit_log()

    # Create user
    user_data = UserCreate(
        username="loginaudituser",
        email="loginaudit@example.com",
        password="LoginAuditPass123",
    )
    AuthService.create_user(db, user_data)

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "loginaudituser",
            "password": "LoginAuditPass123",
        }
    )

    assert response.status_code == 200

    # Check audit log
    events = read_audit_log()
    login_events = [e for e in events if e.get("event_type") == "user:login"]

    assert len(login_events) > 0
    event = login_events[-1]
    assert event["event_type"] == "user:login"
    assert event["resource_type"] == "user"
    assert event["action"] == "login"
    assert event["severity"] == "info"
    assert event["status"] == "success"
    assert event["details"]["username"] == "loginaudituser"


def test_user_login_failed_audit_log(client: TestClient, db: Session):
    """Test that failed login is logged"""
    clear_audit_log()

    # Create user
    user_data = UserCreate(
        username="failaudituser",
        email="failaudit@example.com",
        password="FailAuditPass123",
    )
    AuthService.create_user(db, user_data)

    # Failed login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "failaudituser",
            "password": "WrongPassword",
        }
    )

    assert response.status_code == 401

    # Check audit log
    events = read_audit_log()
    failed_login_events = [e for e in events if e.get("event_type") == "user:login_failed"]

    assert len(failed_login_events) > 0
    event = failed_login_events[-1]
    assert event["event_type"] == "user:login_failed"
    assert event["resource_type"] == "user"
    assert event["action"] == "login"
    assert event["severity"] == "warning"
    assert event["status"] == "failure"
    assert event["details"]["username"] == "failaudituser"
    assert event["details"]["reason"] == "invalid_credentials"


# ============================================================================
# API Key Audit Logging Tests
# ============================================================================

def test_api_key_creation_audit_log(client: TestClient, db: Session):
    """Test that API key creation is logged"""
    clear_audit_log()

    # Create and authenticate user
    user_data = UserCreate(
        username="apikeyuser",
        email="apikey@example.com",
        password="ApiKeyPass123",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={"username": "apikeyuser", "password": "ApiKeyPass123"}
    )
    token = login_response.json()["access_token"]

    # Create API key
    response = client.post(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "test-key"}
    )

    assert response.status_code == 201

    # Check audit log
    events = read_audit_log()
    api_key_created_events = [e for e in events if e.get("event_type") == "api_key:created"]

    assert len(api_key_created_events) > 0
    event = api_key_created_events[-1]
    assert event["event_type"] == "api_key:created"
    assert event["resource_type"] == "api_key"
    assert event["action"] == "create"
    assert event["severity"] == "info"
    assert event["details"]["key_name"] == "test-key"


def test_api_key_deletion_audit_log(client: TestClient, db: Session):
    """Test that API key deletion is logged"""
    clear_audit_log()

    # Create and authenticate user
    user_data = UserCreate(
        username="deletekeyuser",
        email="deletekey@example.com",
        password="DeleteKeyPass123",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={"username": "deletekeyuser", "password": "DeleteKeyPass123"}
    )
    token = login_response.json()["access_token"]

    # Create API key
    create_response = client.post(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "delete-test-key"}
    )
    key_id = create_response.json()["id"]

    # Delete API key
    delete_response = client.delete(
        f"/api/auth/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert delete_response.status_code == 204

    # Check audit log
    events = read_audit_log()
    api_key_deleted_events = [e for e in events if e.get("event_type") == "api_key:deleted"]

    assert len(api_key_deleted_events) > 0
    event = api_key_deleted_events[-1]
    assert event["event_type"] == "api_key:deleted"
    assert event["resource_type"] == "api_key"
    assert event["action"] == "delete"
    assert event["severity"] == "warning"
    assert event["details"]["key_name"] == "delete-test-key"


def test_api_key_revocation_audit_log(client: TestClient, db: Session):
    """Test that API key revocation is logged"""
    clear_audit_log()

    # Create and authenticate user
    user_data = UserCreate(
        username="revokekeyuser",
        email="revokekey@example.com",
        password="RevokeKeyPass123",
    )
    user = AuthService.create_user(db, user_data)

    login_response = client.post(
        "/api/auth/login",
        json={"username": "revokekeyuser", "password": "RevokeKeyPass123"}
    )
    token = login_response.json()["access_token"]

    # Create API key
    create_response = client.post(
        "/api/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "revoke-test-key"}
    )
    key_id = create_response.json()["id"]

    # Revoke API key
    revoke_response = client.post(
        f"/api/auth/api-keys/{key_id}/revoke",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert revoke_response.status_code == 204

    # Check audit log
    events = read_audit_log()
    api_key_revoked_events = [e for e in events if e.get("event_type") == "api_key:revoked"]

    assert len(api_key_revoked_events) > 0
    event = api_key_revoked_events[-1]
    assert event["event_type"] == "api_key:revoked"
    assert event["resource_type"] == "api_key"
    assert event["action"] == "revoke"
    assert event["severity"] == "warning"
    assert event["details"]["key_name"] == "revoke-test-key"


# ============================================================================
# Audit Log Structure Tests
# ============================================================================

def test_audit_event_contains_timestamp(client: TestClient, db: Session):
    """Test that audit events contain timestamps"""
    clear_audit_log()

    user_data = UserCreate(
        username="timestampuser",
        email="timestamp@example.com",
        password="TimestampPass123",
    )

    client.post(
        "/api/auth/register",
        json={
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,
        }
    )

    events = read_audit_log()
    registered_events = [e for e in events if e.get("event_type") == "user:registered"]

    assert len(registered_events) > 0
    event = registered_events[-1]
    assert "timestamp" in event
    assert event["timestamp"]  # Should be a non-empty ISO 8601 string


def test_audit_event_contains_source_ip(client: TestClient, db: Session):
    """Test that audit events contain source IP"""
    clear_audit_log()

    user_data = UserCreate(
        username="ipuser",
        email="ip@example.com",
        password="IpPass123",
    )

    client.post(
        "/api/auth/register",
        json={
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,
        }
    )

    events = read_audit_log()
    registered_events = [e for e in events if e.get("event_type") == "user:registered"]

    assert len(registered_events) > 0
    event = registered_events[-1]
    assert "source_ip" in event


def test_audit_event_severity_levels():
    """Test that different events have appropriate severity levels"""
    info_event = AuditEvent(
        event_type=AuditEventType.USER_LOGIN,
        severity=AuditEventSeverity.INFO,
    )
    assert info_event.severity == AuditEventSeverity.INFO
    assert info_event.to_dict()["severity"] == "info"

    warning_event = AuditEvent(
        event_type=AuditEventType.USER_LOGIN_FAILED,
        severity=AuditEventSeverity.WARNING,
    )
    assert warning_event.severity == AuditEventSeverity.WARNING
    assert warning_event.to_dict()["severity"] == "warning"

    critical_event = AuditEvent(
        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
        severity=AuditEventSeverity.CRITICAL,
    )
    assert critical_event.severity == AuditEventSeverity.CRITICAL
    assert critical_event.to_dict()["severity"] == "critical"


# ============================================================================
# Edge Cases
# ============================================================================

def test_audit_log_with_missing_optional_fields():
    """Test that audit events work with minimal required fields"""
    event = AuditEvent(
        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
    )

    assert event.to_dict()
    assert event.to_json()
    assert event.timestamp is not None


def test_audit_log_with_special_characters_in_details():
    """Test that audit logs handle special characters in details"""
    event = AuditEvent(
        event_type=AuditEventType.USER_REGISTERED,
        details={
            "username": "user@domain.com",
            "email": "test+alias@example.com",
            "special_chars": "!@#$%^&*()",
        }
    )

    json_str = event.to_json()
    parsed = json.loads(json_str)
    assert parsed["details"]["username"] == "user@domain.com"
    assert parsed["details"]["special_chars"] == "!@#$%^&*()"
