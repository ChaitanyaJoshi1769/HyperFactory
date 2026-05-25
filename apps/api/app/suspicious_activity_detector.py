"""Suspicious Activity Detection - Analyze patterns in audit logs to detect attacks"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session as DBSession
from app.models import User
from app.audit_logger import AuditEvent, AuditEventType, AuditEventSeverity
import os
import logging

# Configuration
SUSPICIOUS_ACTIVITY_LOG_FILE = os.getenv("SUSPICIOUS_ACTIVITY_LOG", "logs/suspicious_activity.log")
BRUTE_FORCE_ATTEMPTS_THRESHOLD = int(os.getenv("BRUTE_FORCE_ATTEMPTS_THRESHOLD", "5"))
BRUTE_FORCE_WINDOW_MINUTES = int(os.getenv("BRUTE_FORCE_WINDOW_MINUTES", "15"))
UNUSUAL_TIME_THRESHOLD_HOURS = int(os.getenv("UNUSUAL_TIME_THRESHOLD_HOURS", "3"))
IMPOSSIBLE_TRAVEL_SPEED_KMH = int(os.getenv("IMPOSSIBLE_TRAVEL_SPEED_KMH", "900"))
MAX_FAILED_LOGIN_STREAK = int(os.getenv("MAX_FAILED_LOGIN_STREAK", "3"))


class SuspiciousActivityAlert:
    """Alert for suspicious activity detection"""

    def __init__(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict = None,
        source_ips: List[str] = None,
        detection_time: datetime = None,
    ):
        self.user_id = user_id
        self.alert_type = alert_type  # brute_force, impossible_travel, unusual_login_time, etc.
        self.severity = severity  # low, medium, high, critical
        self.message = message
        self.details = details or {}
        self.source_ips = source_ips or []
        self.detection_time = detection_time or datetime.utcnow()
        self.id = self._generate_alert_id()

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        import secrets
        return f"{self.alert_type}_{secrets.token_hex(4)}"

    def to_json(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "source_ips": self.source_ips,
            "detection_time": self.detection_time.isoformat(),
        }


class SuspiciousActivityDetector:
    """Detects suspicious patterns in user activity and audit logs"""

    def __init__(self):
        """Initialize detector with logger"""
        self.logger = logging.getLogger("suspicious_activity")
        handler = logging.FileHandler(SUSPICIOUS_ACTIVITY_LOG_FILE)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def detect_brute_force_attempts(
        self,
        user_id: str,
        failed_login_count: int,
        time_window_minutes: int = BRUTE_FORCE_WINDOW_MINUTES,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect brute force login attempts.

        Args:
            user_id: User ID
            failed_login_count: Number of failed login attempts
            time_window_minutes: Time window for brute force check

        Returns:
            Alert if suspicious, None otherwise
        """
        if failed_login_count >= BRUTE_FORCE_ATTEMPTS_THRESHOLD:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="brute_force_attempts",
                severity="critical",
                message=f"Brute force attack detected: {failed_login_count} failed login attempts in {time_window_minutes} minutes",
                details={
                    "failed_attempts": failed_login_count,
                    "threshold": BRUTE_FORCE_ATTEMPTS_THRESHOLD,
                    "time_window_minutes": time_window_minutes,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_rapid_location_changes(
        self,
        user_id: str,
        previous_location: Optional[Tuple[str, str]],
        current_location: Tuple[str, str],
        time_difference_seconds: int,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect impossible travel (rapid location changes).

        Args:
            user_id: User ID
            previous_location: (country, city) tuple
            current_location: (country, city) tuple
            time_difference_seconds: Time between logins

        Returns:
            Alert if impossible travel detected
        """
        if not previous_location or previous_location == current_location:
            return None

        # If same country, allow
        if previous_location[0] == current_location[0]:
            return None

        # Assume ~6000 km between countries on average
        distance_km = 6000
        time_hours = time_difference_seconds / 3600

        # Check if speed exceeds commercial flight speed
        if time_hours > 0 and distance_km / time_hours > IMPOSSIBLE_TRAVEL_SPEED_KMH:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="impossible_travel",
                severity="high",
                message=f"Impossible travel detected: {previous_location[1]}, {previous_location[0]} → {current_location[1]}, {current_location[0]} in {time_difference_seconds // 60} minutes",
                details={
                    "previous_location": previous_location,
                    "current_location": current_location,
                    "time_minutes": time_difference_seconds // 60,
                    "estimated_speed_kmh": distance_km / time_hours if time_hours > 0 else float("inf"),
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_unusual_login_time(
        self,
        user_id: str,
        login_times: List[datetime],
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect logins at unusual times compared to user's normal pattern.

        Args:
            user_id: User ID
            login_times: List of recent login times

        Returns:
            Alert if unusual pattern detected
        """
        if not login_times or len(login_times) < 2:
            return None

        # Calculate typical login hours
        login_hours = [t.hour for t in login_times[:-1]]  # Exclude current login
        avg_hour = sum(login_hours) / len(login_hours)
        current_hour = login_times[-1].hour

        # Check if current login is unusual (>3 hours from average)
        if abs(current_hour - avg_hour) > UNUSUAL_TIME_THRESHOLD_HOURS:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="unusual_login_time",
                severity="medium",
                message=f"Login at unusual time: {login_times[-1].strftime('%H:%M')} (typical: ~{int(avg_hour)}:00)",
                details={
                    "current_hour": current_hour,
                    "typical_hour": int(avg_hour),
                    "deviation_hours": abs(current_hour - avg_hour),
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_new_device_login(
        self,
        user_id: str,
        device_name: str,
        previous_devices: List[str],
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect login from new/unknown device.

        Args:
            user_id: User ID
            device_name: Current device name
            previous_devices: List of previous device names

        Returns:
            Alert if new device detected
        """
        if device_name not in previous_devices:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="new_device_login",
                severity="low",
                message=f"Login from new device: {device_name}",
                details={
                    "device_name": device_name,
                    "previous_devices": previous_devices[:5],  # Last 5 devices
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_multiple_failed_attempts_then_success(
        self,
        user_id: str,
        failed_attempts: int,
        followed_by_success: bool,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect pattern of multiple failed attempts followed by successful login.
        May indicate credential stuffing or account takeover.

        Args:
            user_id: User ID
            failed_attempts: Number of recent failed attempts
            followed_by_success: Whether success followed the failures

        Returns:
            Alert if pattern detected
        """
        if failed_attempts >= MAX_FAILED_LOGIN_STREAK and followed_by_success:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="credential_stuffing_pattern",
                severity="high",
                message=f"Credential stuffing pattern: {failed_attempts} failed attempts followed by successful login",
                details={
                    "failed_attempts": failed_attempts,
                    "threshold": MAX_FAILED_LOGIN_STREAK,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_unusual_api_activity(
        self,
        user_id: str,
        requests_per_minute: int,
        baseline_rpm: int = 10,
        anomaly_threshold: float = 5.0,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect unusual API request patterns (possible API abuse/rate limit bypass).

        Args:
            user_id: User ID
            requests_per_minute: Recent request rate
            baseline_rpm: Normal request rate
            anomaly_threshold: Multiplier threshold

        Returns:
            Alert if unusual activity detected
        """
        if requests_per_minute > baseline_rpm * anomaly_threshold:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="unusual_api_activity",
                severity="medium",
                message=f"Unusual API activity: {requests_per_minute} req/min (normal: {baseline_rpm} req/min)",
                details={
                    "requests_per_minute": requests_per_minute,
                    "baseline_rpm": baseline_rpm,
                    "multiplier": requests_per_minute / baseline_rpm,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_multiple_accounts_from_same_ip(
        self,
        ip_address: str,
        accounts_logged_in: List[str],
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect multiple user accounts logging in from the same IP.
        May indicate compromised proxy or account takeover.

        Args:
            ip_address: Source IP address
            accounts_logged_in: List of user IDs logged in from this IP

        Returns:
            Alert if suspicious pattern detected
        """
        if len(accounts_logged_in) > 5:
            alert = SuspiciousActivityAlert(
                user_id=accounts_logged_in[0],  # Alert on first account
                alert_type="multiple_accounts_same_ip",
                severity="high",
                message=f"Multiple accounts ({len(accounts_logged_in)}) logging in from IP {ip_address}",
                details={
                    "ip_address": ip_address,
                    "account_count": len(accounts_logged_in),
                    "accounts": accounts_logged_in[:10],  # First 10
                },
                source_ips=[ip_address],
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_password_reset_abuse(
        self,
        user_id: str,
        reset_count: int,
        window_hours: int = 24,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect excessive password reset requests (account lockout/abuse).

        Args:
            user_id: User ID
            reset_count: Number of reset requests
            window_hours: Time window for requests

        Returns:
            Alert if abuse pattern detected
        """
        if reset_count > 5:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="password_reset_abuse",
                severity="high",
                message=f"Excessive password reset requests: {reset_count} in {window_hours} hours",
                details={
                    "reset_count": reset_count,
                    "time_window_hours": window_hours,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_privilege_escalation_attempt(
        self,
        user_id: str,
        before_role: str,
        after_role: str,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect unauthorized privilege escalation attempts.

        Args:
            user_id: User ID
            before_role: Original role
            after_role: Attempted/new role

        Returns:
            Alert if escalation detected
        """
        if before_role != "admin" and after_role == "admin":
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="privilege_escalation_attempt",
                severity="critical",
                message=f"Privilege escalation attempt: {before_role} → {after_role}",
                details={
                    "before_role": before_role,
                    "after_role": after_role,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def detect_data_exfiltration_pattern(
        self,
        user_id: str,
        large_downloads: int,
        api_exports: int,
    ) -> Optional[SuspiciousActivityAlert]:
        """
        Detect patterns suggesting data exfiltration.

        Args:
            user_id: User ID
            large_downloads: Number of large file downloads
            api_exports: Number of data exports via API

        Returns:
            Alert if suspicious pattern detected
        """
        suspicious_score = large_downloads + (api_exports * 2)

        if suspicious_score > 10:
            alert = SuspiciousActivityAlert(
                user_id=user_id,
                alert_type="data_exfiltration_pattern",
                severity="critical",
                message=f"Data exfiltration pattern detected: {large_downloads} downloads + {api_exports} API exports",
                details={
                    "large_downloads": large_downloads,
                    "api_exports": api_exports,
                    "suspicious_score": suspicious_score,
                },
            )
            self._log_alert(alert)
            return alert

        return None

    def _log_alert(self, alert: SuspiciousActivityAlert) -> None:
        """Log alert to file"""
        self.logger.info(json.dumps(alert.to_json()))

    def get_alerts_for_user(
        self,
        user_id: str,
        alert_type: Optional[str] = None,
        min_severity: str = "low",
    ) -> List[Dict]:
        """
        Retrieve stored alerts for a user (from log file).

        Args:
            user_id: User ID
            alert_type: Optional alert type filter
            min_severity: Minimum severity level (low, medium, high, critical)

        Returns:
            List of alerts
        """
        severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_severity_level = severity_levels.get(min_severity, 0)

        alerts = []

        try:
            with open(SUSPICIOUS_ACTIVITY_LOG_FILE, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)

                        # Filter by user
                        if data.get("user_id") != user_id:
                            continue

                        # Filter by type
                        if alert_type and data.get("alert_type") != alert_type:
                            continue

                        # Filter by severity
                        alert_severity = severity_levels.get(data.get("severity", "low"), 0)
                        if alert_severity < min_severity_level:
                            continue

                        alerts.append(data)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return alerts


# Global detector instance
suspicious_activity_detector = SuspiciousActivityDetector()
