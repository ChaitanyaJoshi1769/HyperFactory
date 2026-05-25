"""Session management tests"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import time

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.session_manager import (
    SessionManager,
    DeviceFingerprint,
    session_manager,
)
from app.models import Session as SessionModel, User


# ============================================================================
# Device Fingerprint Tests
# ============================================================================

def test_device_fingerprint_generation():
    """Test generating device fingerprints"""
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    fingerprint = DeviceFingerprint.generate_fingerprint(user_agent)

    assert fingerprint
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 16  # First 16 chars of SHA256


def test_device_fingerprint_consistency():
    """Test that same user agent produces same fingerprint"""
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    fp1 = DeviceFingerprint.generate_fingerprint(user_agent)
    fp2 = DeviceFingerprint.generate_fingerprint(user_agent)

    assert fp1 == fp2


def test_device_fingerprint_uniqueness():
    """Test that different user agents produce different fingerprints"""
    ua1 = "Mozilla/5.0 (Windows NT 10.0)"
    ua2 = "Mozilla/5.0 (Macintosh; Intel Mac OS X)"

    fp1 = DeviceFingerprint.generate_fingerprint(ua1)
    fp2 = DeviceFingerprint.generate_fingerprint(ua2)

    assert fp1 != fp2


def test_extract_device_name_chrome_windows():
    """Test extracting device name from Chrome on Windows"""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0"

    device_name = DeviceFingerprint.extract_device_name(ua)

    assert "Chrome" in device_name
    assert "Windows" in device_name


def test_extract_device_name_safari_macos():
    """Test extracting device name from Safari on macOS"""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36"

    device_name = DeviceFingerprint.extract_device_name(ua)

    assert "Safari" in device_name
    assert "macOS" in device_name


def test_extract_device_name_firefox_linux():
    """Test extracting device name from Firefox on Linux"""
    ua = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/89.0"

    device_name = DeviceFingerprint.extract_device_name(ua)

    assert "Firefox" in device_name
    assert "Linux" in device_name


def test_extract_device_name_mobile():
    """Test extracting device name from mobile"""
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/537.36"

    device_name = DeviceFingerprint.extract_device_name(ua)

    assert "Safari" in device_name
    assert "iOS" in device_name


def test_extract_device_name_edge():
    """Test extracting device name from Edge"""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/91.0"

    device_name = DeviceFingerprint.extract_device_name(ua)

    assert "Edge" in device_name


def test_extract_device_name_unknown():
    """Test extracting device name from unknown user agent"""
    device_name = DeviceFingerprint.extract_device_name("")

    assert device_name == "Unknown Device"


# ============================================================================
# Session Manager Creation Tests
# ============================================================================

def test_session_manager_creation():
    """Test creating a session manager"""
    manager = SessionManager()

    assert manager.secret_key
    assert manager.token_manager is not None
    assert manager.max_sessions_per_user == 10


def test_create_session(db: Session):
    """Test creating a new session"""
    # Create user
    user_data = UserCreate(
        username="sessionuser",
        email="session@example.com",
        password="SessPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db,
        user,
        ip_address="192.168.1.1",
        user_agent="Chrome on Windows",
        source_ip="192.168.1.1"
    )

    assert token
    assert session
    assert session.user_id == user.id
    assert session.ip_address == "192.168.1.1"
    assert session.is_active
    assert not session.is_trusted


def test_create_session_with_fingerprint(db: Session):
    """Test that session includes device fingerprint"""
    user_data = UserCreate(
        username="fpuser",
        email="fp@example.com",
        password="FPPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    token, session = manager.create_session(
        db,
        user,
        ip_address="192.168.1.1",
        user_agent=ua,
        source_ip="192.168.1.1"
    )

    assert session.device_id
    assert len(session.device_id) == 16
    assert "Chrome" in session.device_name
    assert "Windows" in session.device_name


def test_session_expiration_set(db: Session):
    """Test that session expiration is set correctly"""
    user_data = UserCreate(
        username="expuser",
        email="exp@example.com",
        password="ExpPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    before = datetime.utcnow()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )
    after = datetime.utcnow()

    # Expiration should be 24 hours from now (approximately)
    expected_min = before + timedelta(hours=23, minutes=59)
    expected_max = after + timedelta(hours=24, minutes=1)

    assert expected_min <= session.expires_at <= expected_max


# ============================================================================
# Session Validation Tests
# ============================================================================

def test_validate_session_valid(db: Session):
    """Test validating a valid session"""
    user_data = UserCreate(
        username="validuser",
        email="valid@example.com",
        password="ValidPass1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    is_valid, session_obj, message = manager.validate_session(
        db, token, ip_address="192.168.1.1"
    )

    assert is_valid
    assert session_obj is not None
    assert session_obj.id == session.id


def test_validate_session_invalid_token(db: Session):
    """Test validating invalid session token"""
    manager = SessionManager()

    is_valid, session_obj, message = manager.validate_session(
        db, "invalid-token"
    )

    assert not is_valid
    assert session_obj is None
    assert "Invalid" in message


def test_validate_session_revoked(db: Session):
    """Test validating revoked session"""
    user_data = UserCreate(
        username="revokeduser",
        email="revoked@example.com",
        password="RevPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Revoke the session
    manager.revoke_session(db, str(session.id), source_ip="192.168.1.1")

    is_valid, _, message = manager.validate_session(db, token)

    assert not is_valid
    assert "revoked" in message.lower()


def test_validate_session_expired(db: Session):
    """Test validating expired session"""
    user_data = UserCreate(
        username="expireduser",
        email="expired@example.com",
        password="ExpPass123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Manually expire the session
    session.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    is_valid, _, message = manager.validate_session(db, token)

    assert not is_valid
    assert "expired" in message.lower()


def test_validate_session_ip_mismatch(db: Session):
    """Test validating session with IP mismatch"""
    user_data = UserCreate(
        username="ipmatchuser",
        email="ipmatch@example.com",
        password="IPMatch123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Validate with different IP but don't require match
    is_valid, _, _ = manager.validate_session(
        db, token, ip_address="192.168.1.2", require_ip_match=False
    )

    assert is_valid  # Should still be valid without requirement


def test_validate_session_ip_match_required(db: Session):
    """Test validating session with required IP match"""
    user_data = UserCreate(
        username="ipstrictuser",
        email="ipstrict@example.com",
        password="IPStrict1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Validate with different IP and require match
    is_valid, _, message = manager.validate_session(
        db, token, ip_address="192.168.1.2", require_ip_match=True
    )

    assert not is_valid
    assert "IP" in message or "mismatch" in message.lower()


# ============================================================================
# Session Management Tests
# ============================================================================

def test_get_active_sessions(db: Session):
    """Test getting active sessions for user"""
    user_data = UserCreate(
        username="multisession",
        email="multi@example.com",
        password="Multi123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()

    # Create multiple sessions
    token1, _ = manager.create_session(
        db, user, ip_address="192.168.1.1", user_agent="Chrome"
    )
    token2, _ = manager.create_session(
        db, user, ip_address="192.168.1.2", user_agent="Safari"
    )

    # Get active sessions
    active = manager.get_active_sessions(db, str(user.id))

    assert len(active) == 2
    assert active[0]["device_name"] is not None
    assert active[1]["device_name"] is not None


def test_revoke_session(db: Session):
    """Test revoking a session"""
    user_data = UserCreate(
        username="revoketest",
        email="revoketest@example.com",
        password="RevokeTest1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Revoke session
    success = manager.revoke_session(
        db, str(session.id), reason="User logout", source_ip="192.168.1.1"
    )

    assert success

    # Verify it's revoked
    is_valid, _, _ = manager.validate_session(db, token)
    assert not is_valid


def test_revoke_all_user_sessions(db: Session):
    """Test revoking all user sessions"""
    user_data = UserCreate(
        username="revokealluser",
        email="revokeall@example.com",
        password="RevokeAll1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()

    # Create 3 sessions
    tokens = []
    for i in range(3):
        token, _ = manager.create_session(
            db, user, ip_address=f"192.168.1.{i+1}", source_ip="192.168.1.1"
        )
        tokens.append(token)

    # Revoke all
    count = manager.revoke_all_user_sessions(
        db, str(user.id), reason="Security reset", source_ip="192.168.1.1"
    )

    assert count == 3

    # Verify all are revoked
    for token in tokens:
        is_valid, _, _ = manager.validate_session(db, token)
        assert not is_valid


def test_trust_device(db: Session):
    """Test marking device as trusted"""
    user_data = UserCreate(
        username="trustuser",
        email="trust@example.com",
        password="Trust123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Trust device
    success = manager.trust_device(db, str(session.id), source_ip="192.168.1.1")

    assert success

    # Verify it's trusted
    active = manager.get_active_sessions(db, str(user.id))
    assert active[0]["is_trusted"]


def test_get_suspicious_sessions(db: Session):
    """Test getting suspicious sessions"""
    user_data = UserCreate(
        username="suspicioususer",
        email="suspicious@example.com",
        password="Susp123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Mark as suspicious
    session.suspicious_activity = True
    db.commit()

    suspicious = manager.get_suspicious_sessions(db, str(user.id))

    assert len(suspicious) == 1
    assert suspicious[0]["ip_address"] == "192.168.1.1"


# ============================================================================
# Session Lifecycle Tests
# ============================================================================

def test_max_concurrent_sessions(db: Session):
    """Test enforcing max concurrent sessions per user"""
    user_data = UserCreate(
        username="maxsessionuser",
        email="maxsession@example.com",
        password="MaxSess1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    manager.max_sessions_per_user = 3  # Set low limit

    # Create 4 sessions (should revoke oldest)
    tokens = []
    for i in range(4):
        token, _ = manager.create_session(
            db, user, ip_address=f"192.168.1.{i+1}", source_ip="192.168.1.1"
        )
        tokens.append(token)
        time.sleep(0.01)  # Slight delay to ensure different creation times

    # Check that we still have only 3 active
    active = manager.get_active_sessions(db, str(user.id))
    assert len(active) == 3


def test_cleanup_expired_sessions(db: Session):
    """Test cleanup of expired sessions"""
    user_data = UserCreate(
        username="cleanupuser",
        email="cleanup@example.com",
        password="Cleanup1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    # Manually expire it
    session.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    # Run cleanup
    count = manager.cleanup_expired_sessions(db)

    assert count >= 1

    # Verify it's marked inactive
    is_valid, _, _ = manager.validate_session(db, token)
    assert not is_valid


# ============================================================================
# Edge Cases
# ============================================================================

def test_session_activity_updates(db: Session):
    """Test that session activity is updated on validation"""
    user_data = UserCreate(
        username="activityuser",
        email="activity@example.com",
        password="Activity1",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
    )

    original_activity = session.last_activity
    time.sleep(0.1)

    # Validate session
    manager.validate_session(db, token)

    # Refresh from DB
    db.refresh(session)

    # Activity should be updated
    assert session.last_activity > original_activity


def test_session_token_uniqueness(db: Session):
    """Test that session tokens are unique"""
    user_data = UserCreate(
        username="tokenuser",
        email="token@example.com",
        password="Token123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()

    tokens = set()
    for _ in range(10):
        token, _ = manager.create_session(
            db, user, ip_address="192.168.1.1", source_ip="192.168.1.1"
        )
        tokens.add(token)

    # All tokens should be unique
    assert len(tokens) == 10


def test_session_with_accept_language(db: Session):
    """Test session creation with accept language"""
    user_data = UserCreate(
        username="languser",
        email="lang@example.com",
        password="Lang123",
    )
    user = AuthService.create_user(db, user_data)

    manager = SessionManager()
    token, session = manager.create_session(
        db,
        user,
        ip_address="192.168.1.1",
        user_agent="Chrome",
        accept_language="en-US,en;q=0.9",
        source_ip="192.168.1.1"
    )

    assert session is not None
    assert session.device_id is not None
