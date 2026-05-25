"""Suspicious activity detection tests"""

import pytest
from datetime import datetime, timedelta
from app.suspicious_activity_detector import (
    SuspiciousActivityDetector,
    SuspiciousActivityAlert,
    suspicious_activity_detector,
)


# ============================================================================
# Alert Generation Tests
# ============================================================================

def test_suspicious_activity_alert_creation():
    """Test creating a suspicious activity alert"""
    alert = SuspiciousActivityAlert(
        user_id="user123",
        alert_type="brute_force_attempts",
        severity="critical",
        message="Test alert"
    )

    assert alert.user_id == "user123"
    assert alert.alert_type == "brute_force_attempts"
    assert alert.severity == "critical"
    assert alert.message == "Test alert"
    assert alert.id is not None


def test_alert_to_json():
    """Test converting alert to JSON"""
    alert = SuspiciousActivityAlert(
        user_id="user456",
        alert_type="unusual_login_time",
        severity="medium",
        message="Unusual time",
        details={"hour": 3},
        source_ips=["192.168.1.1"]
    )

    json_data = alert.to_json()

    assert json_data["user_id"] == "user456"
    assert json_data["alert_type"] == "unusual_login_time"
    assert json_data["severity"] == "medium"
    assert json_data["details"]["hour"] == 3
    assert json_data["source_ips"] == ["192.168.1.1"]


def test_alert_id_uniqueness():
    """Test that alerts have unique IDs"""
    alert1 = SuspiciousActivityAlert(
        user_id="u1",
        alert_type="test",
        severity="low",
        message="Test 1"
    )
    alert2 = SuspiciousActivityAlert(
        user_id="u1",
        alert_type="test",
        severity="low",
        message="Test 2"
    )

    assert alert1.id != alert2.id


# ============================================================================
# Brute Force Detection Tests
# ============================================================================

def test_detect_brute_force_below_threshold():
    """Test brute force detection below threshold"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_brute_force_attempts("user1", failed_login_count=3)

    assert alert is None


def test_detect_brute_force_at_threshold():
    """Test brute force detection at threshold"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_brute_force_attempts("user1", failed_login_count=5)

    assert alert is not None
    assert alert.alert_type == "brute_force_attempts"
    assert alert.severity == "critical"
    assert "5 failed login attempts" in alert.message


def test_detect_brute_force_above_threshold():
    """Test brute force detection above threshold"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_brute_force_attempts("user2", failed_login_count=10)

    assert alert is not None
    assert alert.severity == "critical"
    assert alert.details["failed_attempts"] == 10


# ============================================================================
# Location Change Detection Tests
# ============================================================================

def test_detect_rapid_location_change():
    """Test detection of impossible travel"""
    detector = SuspiciousActivityDetector()

    previous = ("United States", "San Francisco")
    current = ("Japan", "Tokyo")
    time_diff = 60  # 60 seconds

    alert = detector.detect_rapid_location_changes(
        "user1",
        previous,
        current,
        time_diff
    )

    assert alert is not None
    assert alert.alert_type == "impossible_travel"
    assert alert.severity == "high"


def test_detect_same_location_no_alert():
    """Test no alert for same location"""
    detector = SuspiciousActivityDetector()

    location = ("United States", "New York")

    alert = detector.detect_rapid_location_changes(
        "user1",
        location,
        location,
        3600
    )

    assert alert is None


def test_detect_same_country_no_alert():
    """Test no alert for same country"""
    detector = SuspiciousActivityDetector()

    previous = ("United States", "New York")
    current = ("United States", "Los Angeles")

    alert = detector.detect_rapid_location_changes(
        "user1",
        previous,
        current,
        7200
    )

    assert alert is None


def test_detect_no_previous_location():
    """Test no alert when no previous location"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_rapid_location_changes(
        "user1",
        None,
        ("Japan", "Tokyo"),
        60
    )

    assert alert is None


# ============================================================================
# Unusual Login Time Detection Tests
# ============================================================================

def test_detect_unusual_login_time():
    """Test detection of unusual login hour"""
    detector = SuspiciousActivityDetector()

    # Normal logins at 9 AM
    normal_times = [
        datetime(2024, 1, 1, 9, 0),
        datetime(2024, 1, 2, 9, 30),
        datetime(2024, 1, 3, 8, 45),
    ]
    # Unusual login at 3 AM
    unusual_time = datetime(2024, 1, 4, 3, 0)

    alert = detector.detect_unusual_login_time(
        "user1",
        normal_times + [unusual_time]
    )

    assert alert is not None
    assert alert.alert_type == "unusual_login_time"
    assert alert.severity == "medium"


def test_detect_usual_login_time():
    """Test no alert for usual login times"""
    detector = SuspiciousActivityDetector()

    # All logins between 8-10 AM
    times = [
        datetime(2024, 1, 1, 8, 0),
        datetime(2024, 1, 2, 9, 30),
        datetime(2024, 1, 3, 10, 0),
        datetime(2024, 1, 4, 9, 15),
    ]

    alert = detector.detect_unusual_login_time("user1", times)

    assert alert is None


def test_detect_unusual_login_time_insufficient_history():
    """Test no alert with insufficient history"""
    detector = SuspiciousActivityDetector()

    times = [datetime(2024, 1, 1, 9, 0)]

    alert = detector.detect_unusual_login_time("user1", times)

    assert alert is None


# ============================================================================
# New Device Detection Tests
# ============================================================================

def test_detect_new_device():
    """Test detection of new device login"""
    detector = SuspiciousActivityDetector()

    previous_devices = ["Chrome on Windows", "Safari on macOS"]
    new_device = "Firefox on Linux"

    alert = detector.detect_new_device_login(
        "user1",
        new_device,
        previous_devices
    )

    assert alert is not None
    assert alert.alert_type == "new_device_login"
    assert alert.severity == "low"
    assert new_device in alert.message


def test_detect_known_device():
    """Test no alert for known device"""
    detector = SuspiciousActivityDetector()

    previous_devices = ["Chrome on Windows", "Safari on macOS"]
    known_device = "Chrome on Windows"

    alert = detector.detect_new_device_login(
        "user1",
        known_device,
        previous_devices
    )

    assert alert is None


# ============================================================================
# Credential Stuffing Pattern Detection Tests
# ============================================================================

def test_detect_credential_stuffing_pattern():
    """Test detection of credential stuffing pattern"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_multiple_failed_attempts_then_success(
        "user1",
        failed_attempts=5,
        followed_by_success=True
    )

    assert alert is not None
    assert alert.alert_type == "credential_stuffing_pattern"
    assert alert.severity == "high"


def test_detect_no_credential_stuffing_no_success():
    """Test no alert without successful login"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_multiple_failed_attempts_then_success(
        "user1",
        failed_attempts=5,
        followed_by_success=False
    )

    assert alert is None


def test_detect_no_credential_stuffing_few_failures():
    """Test no alert with few failures"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_multiple_failed_attempts_then_success(
        "user1",
        failed_attempts=2,
        followed_by_success=True
    )

    assert alert is None


# ============================================================================
# Unusual API Activity Detection Tests
# ============================================================================

def test_detect_unusual_api_activity():
    """Test detection of unusual API request rate"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_unusual_api_activity(
        "user1",
        requests_per_minute=100,
        baseline_rpm=10,
        anomaly_threshold=5.0
    )

    assert alert is not None
    assert alert.alert_type == "unusual_api_activity"
    assert alert.severity == "medium"
    assert "100 req/min" in alert.message


def test_detect_normal_api_activity():
    """Test no alert for normal API activity"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_unusual_api_activity(
        "user1",
        requests_per_minute=15,
        baseline_rpm=10,
        anomaly_threshold=5.0
    )

    assert alert is None


# ============================================================================
# Multiple Accounts Same IP Detection Tests
# ============================================================================

def test_detect_multiple_accounts_same_ip():
    """Test detection of multiple accounts from same IP"""
    detector = SuspiciousActivityDetector()

    accounts = ["user1", "user2", "user3", "user4", "user5", "user6"]

    alert = detector.detect_multiple_accounts_from_same_ip(
        "192.168.1.100",
        accounts
    )

    assert alert is not None
    assert alert.alert_type == "multiple_accounts_same_ip"
    assert alert.severity == "high"
    assert "6" in alert.message


def test_detect_single_account_same_ip():
    """Test no alert for single account from IP"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_multiple_accounts_from_same_ip(
        "192.168.1.100",
        ["user1"]
    )

    assert alert is None


def test_detect_few_accounts_same_ip():
    """Test no alert for few accounts from IP"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_multiple_accounts_from_same_ip(
        "192.168.1.100",
        ["user1", "user2", "user3"]
    )

    assert alert is None


# ============================================================================
# Password Reset Abuse Detection Tests
# ============================================================================

def test_detect_password_reset_abuse():
    """Test detection of excessive password reset requests"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_password_reset_abuse(
        "user1",
        reset_count=10,
        window_hours=24
    )

    assert alert is not None
    assert alert.alert_type == "password_reset_abuse"
    assert alert.severity == "high"


def test_detect_normal_password_resets():
    """Test no alert for normal reset activity"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_password_reset_abuse(
        "user1",
        reset_count=2,
        window_hours=24
    )

    assert alert is None


# ============================================================================
# Privilege Escalation Detection Tests
# ============================================================================

def test_detect_privilege_escalation():
    """Test detection of privilege escalation"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_privilege_escalation_attempt(
        "user1",
        before_role="user",
        after_role="admin"
    )

    assert alert is not None
    assert alert.alert_type == "privilege_escalation_attempt"
    assert alert.severity == "critical"


def test_detect_no_privilege_escalation():
    """Test no alert for normal role changes"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_privilege_escalation_attempt(
        "user1",
        before_role="user",
        after_role="manager"
    )

    assert alert is None


def test_detect_admin_to_admin():
    """Test no alert for admin staying admin"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_privilege_escalation_attempt(
        "admin1",
        before_role="admin",
        after_role="admin"
    )

    assert alert is None


# ============================================================================
# Data Exfiltration Pattern Detection Tests
# ============================================================================

def test_detect_data_exfiltration_pattern():
    """Test detection of data exfiltration pattern"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_data_exfiltration_pattern(
        "user1",
        large_downloads=8,
        api_exports=3
    )

    assert alert is not None
    assert alert.alert_type == "data_exfiltration_pattern"
    assert alert.severity == "critical"


def test_detect_normal_data_activity():
    """Test no alert for normal data activity"""
    detector = SuspiciousActivityDetector()

    alert = detector.detect_data_exfiltration_pattern(
        "user1",
        large_downloads=2,
        api_exports=1
    )

    assert alert is None


# ============================================================================
# Alert Storage and Retrieval Tests
# ============================================================================

def test_log_and_retrieve_alert():
    """Test logging and retrieving alerts"""
    detector = SuspiciousActivityDetector()

    # Generate an alert
    alert = detector.detect_brute_force_attempts("testuser", 10)

    # Try to retrieve it
    alerts = detector.get_alerts_for_user("testuser", alert_type="brute_force_attempts")

    # Should have at least one alert
    assert len(alerts) >= 1
    assert alerts[-1]["user_id"] == "testuser"
    assert alerts[-1]["alert_type"] == "brute_force_attempts"


def test_retrieve_alerts_by_severity():
    """Test retrieving alerts filtered by severity"""
    detector = SuspiciousActivityDetector()

    # Generate multiple alerts
    detector.detect_brute_force_attempts("user1", 10)
    detector.detect_new_device_login("user1", "Firefox", ["Chrome"])

    # Retrieve only critical alerts
    alerts = detector.get_alerts_for_user("user1", min_severity="critical")

    assert all(a["severity"] == "critical" for a in alerts)


def test_retrieve_alerts_empty_user():
    """Test retrieving alerts for user with no alerts"""
    detector = SuspiciousActivityDetector()

    alerts = detector.get_alerts_for_user("nonexistent_user")

    # Should be empty or contain only alerts from other tests
    # Filter to just this user
    user_alerts = [a for a in alerts if a["user_id"] == "nonexistent_user"]
    assert len(user_alerts) == 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_detector_instance_exists():
    """Test that global detector instance exists"""
    assert suspicious_activity_detector is not None
    assert isinstance(suspicious_activity_detector, SuspiciousActivityDetector)


def test_multiple_detection_types_for_user():
    """Test generating multiple different alert types for same user"""
    detector = SuspiciousActivityDetector()

    # Generate different types of alerts
    alert1 = detector.detect_brute_force_attempts("user1", 5)
    alert2 = detector.detect_new_device_login("user1", "Firefox", ["Chrome"])
    alert3 = detector.detect_unusual_login_time("user1", [
        datetime(2024, 1, 1, 9, 0),
        datetime(2024, 1, 2, 9, 30),
        datetime(2024, 1, 3, 3, 0),  # Unusual time
    ])

    assert alert1 is not None
    assert alert2 is not None
    assert alert3 is not None
    assert alert1.alert_type != alert2.alert_type
    assert alert2.alert_type != alert3.alert_type
