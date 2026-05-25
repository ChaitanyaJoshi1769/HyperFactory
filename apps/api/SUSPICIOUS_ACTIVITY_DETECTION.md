# Suspicious Activity Detection - Pattern-Based Security Alerting

## Overview

HyperFactory implements intelligent suspicious activity detection that analyzes user behavior patterns and audit logs to identify potential security threats. The system detects common attack patterns including brute-force attempts, impossible travel, credential stuffing, privilege escalation, and data exfiltration—enabling security teams to respond quickly to threats.

## Features

✅ **Brute Force Detection**
- Failed login attempt tracking
- Configurable threshold and time window (default: 5 attempts in 15 minutes)
- Immediate alert on suspicious pattern detection
- Integration with account lockout system

✅ **Impossible Travel Detection**
- Rapid location changes (country to country in minutes)
- Commercial flight speed baseline (900 km/h)
- Geographic analysis from login locations
- Real-time alerting on impossible travel patterns

✅ **Login Anomaly Detection**
- Unusual login times (compared to user baseline)
- New device detection (first login from device)
- New geolocation detection
- Behavioral baseline learning

✅ **Credential Stuffing Detection**
- Multiple failed attempts followed by successful login
- Pattern suggests credential database breach
- Distinguishes from legitimate forgotten password scenarios
- Automated alerting for further investigation

✅ **API Abuse Detection**
- Unusual request rate patterns
- Baseline establishment per user/API key
- Real-time rate anomaly detection
- Prevents API scraping and data exfiltration

✅ **Account Compromise Detection**
- Multiple accounts from single IP
- Privilege escalation attempts
- Unauthorized role changes
- Password reset abuse (account takeover indicator)
- Data exfiltration patterns

✅ **Alert Management**
- Severity levels: low, medium, high, critical
- Alert logging to separate file for SIEM integration
- Alert retrieval API for dashboard display
- Filtering by alert type and severity
- User-centric alert history

✅ **Security Operations**
- Non-blocking detection (alerts don't interrupt service)
- Integration with audit logging
- Alert enrichment with context (IP, location, device)
- Historical alert storage for forensics
- Pattern-based intelligence gathering

## Architecture

### SuspiciousActivityAlert Class

Represents a security alert:

```python
from app.suspicious_activity_detector import SuspiciousActivityAlert

alert = SuspiciousActivityAlert(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    alert_type="brute_force_attempts",  # Type of alert
    severity="critical",                 # low, medium, high, critical
    message="Brute force attack detected: 5 failed attempts",
    details={                           # Context-specific details
        "failed_attempts": 5,
        "threshold": 5,
        "time_window_minutes": 15
    },
    source_ips=["192.168.1.1"],        # Associated IPs
)

# Convert to JSON for storage
json_data = alert.to_json()
```

### SuspiciousActivityDetector Class

Core detection engine with multiple pattern detectors:

```python
from app.suspicious_activity_detector import suspicious_activity_detector

# Detect brute force attempts
alert = suspicious_activity_detector.detect_brute_force_attempts(
    user_id="user123",
    failed_login_count=5,
    time_window_minutes=15
)

# Detect impossible travel
alert = suspicious_activity_detector.detect_rapid_location_changes(
    user_id="user123",
    previous_location=("United States", "San Francisco"),
    current_location=("Japan", "Tokyo"),
    time_difference_seconds=60
)

# Detect unusual login time
alert = suspicious_activity_detector.detect_unusual_login_time(
    user_id="user123",
    login_times=[datetime(2024,1,1,9,0), datetime(2024,1,4,3,0)]
)

# Detect new device login
alert = suspicious_activity_detector.detect_new_device_login(
    user_id="user123",
    device_name="Firefox on Linux",
    previous_devices=["Chrome on Windows", "Safari on macOS"]
)

# Detect credential stuffing pattern
alert = suspicious_activity_detector.detect_multiple_failed_attempts_then_success(
    user_id="user123",
    failed_attempts=5,
    followed_by_success=True
)

# Detect unusual API activity
alert = suspicious_activity_detector.detect_unusual_api_activity(
    user_id="user123",
    requests_per_minute=100,
    baseline_rpm=10,
    anomaly_threshold=5.0
)

# Detect multiple accounts from same IP (credential stuffing/botnet)
alert = suspicious_activity_detector.detect_multiple_accounts_from_same_ip(
    ip_address="192.168.1.100",
    accounts_logged_in=["user1", "user2", "user3", "user4", "user5", "user6"]
)

# Detect password reset abuse
alert = suspicious_activity_detector.detect_password_reset_abuse(
    user_id="user123",
    reset_count=10,
    window_hours=24
)

# Detect privilege escalation
alert = suspicious_activity_detector.detect_privilege_escalation_attempt(
    user_id="user123",
    before_role="user",
    after_role="admin"
)

# Detect data exfiltration pattern
alert = suspicious_activity_detector.detect_data_exfiltration_pattern(
    user_id="user123",
    large_downloads=8,
    api_exports=3
)

# Retrieve alerts for user
alerts = suspicious_activity_detector.get_alerts_for_user(
    user_id="user123",
    alert_type="brute_force_attempts",  # Optional filter
    min_severity="high"                 # Filter by severity
)
```

## Detection Rules

### Brute Force Attempts

```
Trigger: >= 5 failed login attempts within 15 minutes
Severity: CRITICAL
Response: Alert + Account lockout (if enabled)
Bypass: Whitelist legitimate tool automation
```

### Impossible Travel

```
Trigger: Login from different country in < travel time
Speed Check: Compare against 900 km/h commercial flight speed
Severity: HIGH
Response: Alert + Optional 2FA requirement
Note: Account for flight times, consider time zones
```

### Unusual Login Time

```
Trigger: Login hour > 3 hours from user's average
Analysis: Last 10 logins, extract hour of day
Severity: MEDIUM
Response: Alert + Optional verification
Note: Account for shift work, travel, time zone changes
```

### New Device Login

```
Trigger: First login from device (based on fingerprint)
Analysis: Compare device name against history
Severity: LOW
Response: Alert + Optional trust/verify
Note: Browser updates may trigger false positives
```

### Credential Stuffing Pattern

```
Trigger: 3+ failed attempts followed by successful login
Scenario: Attacker testing credentials from leaked database
Severity: HIGH
Response: Alert + Force password change
Analysis: Timing and pattern matter
```

### Unusual API Activity

```
Trigger: Request rate > baseline * 5x
Baseline: Per-user normal request rate (default 10 req/min)
Severity: MEDIUM
Response: Alert + Optional rate limit reduction
Analysis: Distinguish bulk operations vs automated scraping
```

### Multiple Accounts Same IP

```
Trigger: 6+ accounts logging in from same IP
Scenario: Botnet, compromised proxy, or credential stuffing
Severity: HIGH
Response: Alert + Optional IP block
Analysis: VPN/corporate proxy may trigger false positives
```

### Password Reset Abuse

```
Trigger: > 5 reset requests in 24 hours
Scenario: Account takeover or targeted attack
Severity: HIGH
Response: Alert + Email notification + Account review
Note: Distinguish forgotten password from attack
```

### Privilege Escalation

```
Trigger: Non-admin user assigned admin role
Scenario: Unauthorized role modification (code injection, SSRF, etc.)
Severity: CRITICAL
Response: Alert + Immediate role revert + Investigation
Analysis: Should not occur in normal flow
```

### Data Exfiltration Pattern

```
Trigger: (Large downloads + API exports) score > 10
Scoring: downloads * 1 + api_exports * 2
Scenario: Insider threat or account compromise
Severity: CRITICAL
Response: Alert + Session revocation + Investigation
Analysis: Combines multiple data access patterns
```

## Configuration

### Environment Variables

```bash
# Detection thresholds
BRUTE_FORCE_ATTEMPTS_THRESHOLD=5            # Attempts
BRUTE_FORCE_WINDOW_MINUTES=15               # Time window
UNUSUAL_TIME_THRESHOLD_HOURS=3              # Hours from average
IMPOSSIBLE_TRAVEL_SPEED_KMH=900             # km/h
MAX_FAILED_LOGIN_STREAK=3                   # Attempts
SUSPICIOUS_ACTIVITY_LOG=logs/suspicious_activity.log
```

### Application Settings

Modify in `app/suspicious_activity_detector.py`:

```python
# Change brute force threshold
BRUTE_FORCE_ATTEMPTS_THRESHOLD = 3  # 3 attempts instead of 5

# Change time window
BRUTE_FORCE_WINDOW_MINUTES = 30  # 30 minutes instead of 15
```

## Integration Examples

### Login Endpoint Integration

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.suspicious_activity_detector import suspicious_activity_detector
from app.services.auth_service import AuthService

@router.post("/login")
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login with suspicious activity detection"""
    
    # Attempt authentication
    user = AuthService.authenticate_user(db, credentials)
    
    if not user:
        # Track failed login
        failed_attempt = db.query(...).filter(...).count()
        
        # Check for brute force
        alert = suspicious_activity_detector.detect_brute_force_attempts(
            user_id=str(user.id) if user else credentials.username,
            failed_login_count=failed_attempt
        )
        
        if alert:
            # Trigger response (block, 2FA, etc.)
            raise HTTPException(status_code=429, detail="Too many attempts")
    
    return {"access_token": token}
```

### Periodic Alert Review

```python
def review_suspicious_alerts(user_id: str):
    """Security team reviews alerts"""
    from app.suspicious_activity_detector import suspicious_activity_detector
    
    # Get all alerts for user
    alerts = suspicious_activity_detector.get_alerts_for_user(
        user_id=user_id,
        min_severity="high"
    )
    
    for alert in alerts:
        # Analysis logic
        if alert["alert_type"] == "brute_force_attempts":
            # Recommend password change
            pass
        elif alert["alert_type"] == "privilege_escalation_attempt":
            # Immediate investigation required
            pass
        elif alert["alert_type"] == "data_exfiltration_pattern":
            # Revoke sessions, investigate
            pass
```

## Testing

Comprehensive test suite in `tests/test_suspicious_activity_detector.py`:

```bash
# Run all detection tests
python3 -m pytest tests/test_suspicious_activity_detector.py -v

# Test specific detection
python3 -m pytest tests/test_suspicious_activity_detector.py::test_detect_brute_force_at_threshold -v
python3 -m pytest tests/test_suspicious_activity_detector.py::test_detect_impossible_travel -v
python3 -m pytest tests/test_suspicious_activity_detector.py::test_detect_credential_stuffing_pattern -v
```

### Test Coverage

- Brute force detection (below, at, above threshold)
- Impossible travel detection (rapid country changes)
- Unusual login time detection
- New device detection
- Credential stuffing pattern detection
- API abuse detection
- Multiple accounts from same IP
- Password reset abuse detection
- Privilege escalation detection
- Data exfiltration pattern detection
- Alert storage and retrieval
- Alert filtering by type and severity
- Multiple detection types for same user

## Alert Format

Alerts are stored as JSON lines in `logs/suspicious_activity.log`:

```json
{
  "id": "brute_force_9a4c",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "alert_type": "brute_force_attempts",
  "severity": "critical",
  "message": "Brute force attack detected: 5 failed login attempts in 15 minutes",
  "details": {
    "failed_attempts": 5,
    "threshold": 5,
    "time_window_minutes": 15
  },
  "source_ips": ["192.168.1.1"],
  "detection_time": "2024-01-15T14:32:45.123456"
}
```

## Severity Levels

- **LOW**: Informational, likely not malicious (new device, unusual time)
- **MEDIUM**: Potentially suspicious, investigate (unusual API activity, new location)
- **HIGH**: Likely attack (credential stuffing, impossible travel, multiple accounts)
- **CRITICAL**: Active attack (brute force, privilege escalation, data exfiltration)

## Performance Impact

- **Detection Operations**: < 1ms (in-memory pattern matching)
- **Alert Storage**: < 10ms (JSON file write)
- **Alert Retrieval**: 10-100ms (depends on file size)
- **Integration Overhead**: < 5ms per endpoint

For typical usage (1000 users, 10 alerts per day):
```
Detection: ~10ms per detection call
Storage: 10 alerts * 10ms = 100ms per day total
Retrieval: < 1 second for entire day's alerts
```

## Security Considerations

⚠️ **Current Implementation**

- Alerts stored in plaintext JSON (add encryption for sensitive environments)
- No alert deduplication (same alert may appear multiple times)
- No machine learning (rule-based only)
- No integration with external threat intelligence

✅ **Best Practices**

1. **False Positive Management**
   - Implement user whitelist for trusted activities
   - Allow users to mark devices as trusted
   - Learn individual user patterns over time
   - Provide feedback mechanism for analysts

2. **Alert Fatigue Prevention**
   - Aggregate similar alerts
   - Group by user and alert type
   - Set minimum time between duplicate alerts
   - Prioritize by severity and recency

3. **Response Automation**
   - Auto-lock on brute force
   - Auto-2FA on new location
   - Auto-revoke on privilege escalation
   - Manual review for medium-severity items

4. **Data Retention**
   - Archive old alerts (>30 days)
   - Retain for forensics (>1 year)
   - Encrypt sensitive alert details
   - Comply with data retention policies

5. **Threat Intelligence**
   - Flag IPs seen in multiple accounts
   - Track compromised credential sources
   - Monitor for coordinated attacks
   - Share with threat intelligence platforms

## Future Enhancements

### Machine Learning

```python
def detect_anomaly_using_ml(user_id: str, features: Dict) -> bool:
    """Detect anomalies using trained ML model"""
    # Train on 60 days of user behavior
    # Detect statistically unusual patterns
    # Reduce false positives with confidence scores
    pass
```

### Geolocation Services

```python
def enrich_alert_with_location(ip_address: str) -> Dict:
    """Add geographic context to alerts"""
    # Integrate MaxMind or IP2Location
    # Calculate distance and travel time
    # Detect VPN/proxy usage
    return {"country": "...", "city": "..."}
```

### Alert Aggregation

```python
def aggregate_similar_alerts(alerts: List[Dict]) -> List[Dict]:
    """Group and deduplicate similar alerts"""
    # Same user, same type within 5 minutes = one alert
    # Count occurrences for severity boost
    # Summarize in dashboard
    pass
```

### Automated Response

```python
def auto_respond_to_alert(alert: SuspiciousActivityAlert) -> None:
    """Automatically respond based on severity"""
    if alert.severity == "critical":
        revoke_all_sessions(alert.user_id)
        notify_security_team(alert)
        trigger_incident_response()
    elif alert.severity == "high":
        enforce_2fa(alert.user_id)
        notify_user(alert)
```

## Compliance

Suspicious activity detection helps meet compliance requirements:

- **OWASP**: A02:2021 - Cryptographic Failures (detect attacks)
- **NIST SP 800-63**: Threat and error reporting (800-63A-7.1)
- **PCI DSS**: Requirement 6.5.10 (monitor for attacks)
- **GDPR**: Security of personal data
- **SOC 2**: Monitoring and alerting on security events

## Troubleshooting

**Too many false positives**
- Increase threshold values
- Implement whitelist for known behaviors
- Analyze alert patterns to refine rules
- Consider user context (travel, shift work)

**Missing detection on known attacks**
- Lower detection thresholds
- Add new detection rules for specific threats
- Correlate multiple alert types
- Integrate with threat intelligence

**Alert storage growing too large**
- Archive old alerts (>30 days)
- Compress log files periodically
- Implement log rotation
- Use separate database for long-term storage

**Low alert volume despite known issues**
- Verify audit logging is enabled
- Check alert detection is enabled in endpoints
- Trace through detection logic
- Add debug logging to detector

## Conclusion

Suspicious Activity Detection provides critical visibility into threats:

- ✅ Detects common attack patterns in real-time
- ✅ Provides context for incident response teams
- ✅ Enables proactive security monitoring
- ✅ Supports compliance and security audits
- ✅ Non-blocking, doesn't impact user experience

For production deployments, implement:
1. Suspicious activity detector integration
2. Alert storage and retrieval endpoints
3. Security team dashboard
4. Automated response actions
5. Alert tuning and false positive management
6. Integration with SIEM systems
7. Periodic review and threat analysis

See AUDIT_LOGGING.md, SESSION_MANAGEMENT.md, and ACCOUNT_LOCKOUT.md for complementary security features.
