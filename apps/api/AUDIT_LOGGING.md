# Audit Logging - Security Event Tracking

## Overview

HyperFactory implements comprehensive audit logging for security-critical events. The system tracks user authentication, API key management, permission denials, and suspicious activities with structured, JSON-serialized event logs stored in `logs/audit.log`.

## Features

✅ **Comprehensive Event Tracking**
- User registration, login (success/failure), password changes, logout
- API key creation, deletion, and revocation
- Permission denials and access control decisions
- Suspicious activities and security alerts
- Rate limiting violations

✅ **Structured Event Data**
- Standardized event format with type, actor, resource, and action
- Severity levels (INFO, WARNING, CRITICAL)
- Timestamp with UTC precision
- Source IP address for client tracking
- Event-specific details in JSON

✅ **JSON Serialization**
- Machine-readable format for log aggregation
- Compatible with logging systems and SIEM platforms
- Timestamp in ISO 8601 format
- Nested details for rich context

✅ **Severity Levels**
- **INFO**: Normal operations (login success, registration, API key creation)
- **WARNING**: Suspicious but expected events (failed login, rate limiting, permission denied, API key deletion)
- **CRITICAL**: Security incidents (suspicious activity, account lockout, user deletion)

✅ **Client Identification**
- Source IP address from X-Forwarded-For header (proxied requests)
- Falls back to direct client IP for non-proxied requests
- User identification through actor_id field

## Architecture

### AuditEvent Class

Core data model for audit events:

```python
from app.audit_logger import AuditEvent, AuditEventType, AuditEventSeverity

event = AuditEvent(
    event_type=AuditEventType.USER_LOGIN,
    actor_id="user-uuid",
    resource_id="user-uuid",
    resource_type="user",
    action="login",
    severity=AuditEventSeverity.INFO,
    details={"username": "john@example.com"},
    source_ip="192.168.1.100",
    status="success"
)

# Convert to dictionary
event_dict = event.to_dict()

# Convert to JSON
json_str = event.to_json()
```

### AuditEventType Enum

Supported event types:

**Authentication Events**
- `USER_REGISTERED`: User registration
- `USER_LOGIN`: Successful user login
- `USER_LOGIN_FAILED`: Failed login attempt
- `USER_LOGOUT`: User logout
- `USER_PASSWORD_CHANGED`: Password change
- `USER_PASSWORD_RESET`: Password reset

**API Key Management**
- `API_KEY_CREATED`: New API key created
- `API_KEY_DELETED`: API key deleted
- `API_KEY_REVOKED`: API key revoked

**User Management**
- `USER_ACTIVATED`: User account activated
- `USER_DEACTIVATED`: User account deactivated
- `USER_DELETED`: User account deleted
- `USER_ROLE_CHANGED`: User role/permissions changed
- `USER_ADMIN_STATUS_CHANGED`: Admin status changed

**Rate Limiting**
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded

**Security Events**
- `SUSPICIOUS_ACTIVITY`: Suspicious activity detected
- `ACCOUNT_LOCKOUT`: Account locked after failures
- `PERMISSION_DENIED`: Permission check failed

**Data Operations**
- `DATA_EXPORT`: Data exported
- `DATA_IMPORT`: Data imported
- `DATA_DELETE`: Data deleted

### AuditLogger Class

High-level logging interface:

```python
from app.audit_logger import audit_logger

# Log user registration
audit_logger.log_user_registered(
    user_id="uuid",
    username="john",
    email="john@example.com",
    source_ip="192.168.1.100"
)

# Log login attempt (success)
audit_logger.log_user_login(
    user_id="uuid",
    username="john",
    source_ip="192.168.1.100"
)

# Log login failure
audit_logger.log_user_login_failed(
    username="john",
    reason="invalid_credentials",
    source_ip="192.168.1.100"
)

# Log API key operations
audit_logger.log_api_key_created(
    user_id="uuid",
    key_id="key-uuid",
    key_name="prod-api-key",
    source_ip="192.168.1.100"
)

audit_logger.log_api_key_deleted(
    user_id="uuid",
    key_id="key-uuid",
    key_name="prod-api-key",
    source_ip="192.168.1.100"
)

audit_logger.log_api_key_revoked(
    user_id="uuid",
    key_id="key-uuid",
    key_name="prod-api-key",
    source_ip="192.168.1.100"
)

# Log permission denied
audit_logger.log_permission_denied(
    user_id="uuid",
    resource_id="resource-uuid",
    resource_type="factory",
    required_permission="admin",
    source_ip="192.168.1.100"
)

# Log suspicious activity
audit_logger.log_suspicious_activity(
    user_id="uuid",
    activity_type="brute_force_attempt",
    description="Multiple failed logins from same IP",
    source_ip="192.168.1.100"
)

# Log user deletion
audit_logger.log_user_deleted(
    admin_id="admin-uuid",
    deleted_user_id="user-uuid",
    deleted_username="john",
    reason="account_compromise",
    source_ip="192.168.1.100"
)
```

### Global Audit Logger Instance

The module provides a global audit logger instance:

```python
from app.audit_logger import audit_logger

# Use directly - already initialized
audit_logger.log_user_login(user_id, username, source_ip)
```

## Integration with Authentication Endpoints

The audit logger is integrated into the authentication router:

```python
from app.audit_logger import audit_logger

@router.post("/register")
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_identifier(request)
    
    # ... validation and rate limiting ...
    
    db_user = AuthService.create_user(db, user)
    
    # Log successful registration
    audit_logger.log_user_registered(
        user_id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        source_ip=client_ip
    )
    
    return db_user

@router.post("/login")
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_identifier(request)
    
    # ... rate limiting ...
    
    user = AuthService.authenticate_user(db, credentials)
    
    if not user:
        # Log failed login
        audit_logger.log_user_login_failed(
            username=credentials.username,
            reason="invalid_credentials",
            source_ip=client_ip
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = AuthService.create_access_token_for_user(user, ...)
    
    # Log successful login
    audit_logger.log_user_login(
        user_id=str(user.id),
        username=user.username,
        source_ip=client_ip
    )
    
    return TokenResponse(access_token=access_token, ...)
```

## Log File Format

Audit logs are written to `logs/audit.log` in the following format:

```
timestamp - logger_name - level - json_event
```

Example:
```
2026-05-25 10:30:45,123 - hyperfactory.audit - INFO - {"timestamp": "2026-05-25T10:30:45.123456", "event_type": "user:login", "actor_id": "550e8400-e29b-41d4-a716-446655440000", "resource_id": "550e8400-e29b-41d4-a716-446655440000", "resource_type": "user", "action": "login", "severity": "info", "details": {"username": "john@example.com"}, "source_ip": "192.168.1.100", "status": "success"}
```

## Parsing Audit Logs

Extract JSON events from the log file:

```python
import json

def read_audit_log():
    events = []
    with open('logs/audit.log', 'r') as f:
        for line in f:
            # Parse: "timestamp - name - level - json"
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                try:
                    event = json.loads(parts[3].strip())
                    events.append(event)
                except json.JSONDecodeError:
                    pass
    return events

# Read and filter events
events = read_audit_log()
logins = [e for e in events if e['event_type'] == 'user:login']
failed_logins = [e for e in events if e['event_type'] == 'user:login_failed']
```

## Event Data Structure

Each audit event in the log contains:

```json
{
  "timestamp": "2026-05-25T10:30:45.123456",
  "event_type": "user:login",
  "actor_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_type": "user",
  "action": "login",
  "severity": "info",
  "details": {
    "username": "john@example.com"
  },
  "source_ip": "192.168.1.100",
  "status": "success"
}
```

### Field Descriptions

- **timestamp**: ISO 8601 UTC timestamp of the event
- **event_type**: Category and type of event (e.g., "user:login")
- **actor_id**: UUID of the user performing the action (null for unauthenticated events)
- **resource_id**: UUID of the affected resource (user, API key, etc.)
- **resource_type**: Type of resource ("user", "api_key", "factory", etc.)
- **action**: What happened ("login", "create", "delete", "revoke", etc.)
- **severity**: Event severity level ("info", "warning", "critical")
- **details**: Event-specific additional information as JSON object
- **source_ip**: IP address of the request source
- **status**: Outcome ("success", "failure", "blocked", "denied")

## Security Considerations

⚠️ **Current Implementation**

- Logs written to local filesystem
- No encryption of log data
- No log rotation built-in
- Event details may contain usernames/emails

✅ **Best Practices**

1. **Secure Log Storage**
   - Store logs in secure location with appropriate file permissions (mode 0600)
   - Consider separate partition for audit logs
   - Implement log rotation to manage file size

2. **Log Protection**
   - Restrict read access to audit logs (admin only)
   - Consider encrypting sensitive log files
   - Hash or mask sensitive data in details if needed

3. **Log Monitoring**
   - Implement alerting for critical severity events
   - Monitor failed login patterns for brute force attacks
   - Track suspicious activity and permission denials

4. **Log Retention**
   - Define retention policy (e.g., 90 days, 1 year)
   - Archive old logs separately
   - Consider SIEM integration for centralized logging

5. **Compliance**
   - Audit logs help meet regulatory requirements
   - Maintain detailed records for incident investigation
   - Use logs to demonstrate security controls

## Example: Monitoring Brute Force Attacks

```python
import json
from collections import defaultdict

def detect_brute_force(log_file='logs/audit.log', threshold=5, window_minutes=5):
    """Detect potential brute force attacks"""
    failed_logins = defaultdict(list)
    
    with open(log_file, 'r') as f:
        for line in f:
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                event = json.loads(parts[3].strip())
                if event['event_type'] == 'user:login_failed':
                    username = event['details']['username']
                    failed_logins[username].append(event['timestamp'])
    
    # Check for threshold violations
    alerts = []
    for username, timestamps in failed_logins.items():
        if len(timestamps) >= threshold:
            alerts.append({
                'username': username,
                'failed_attempts': len(timestamps),
                'first_attempt': timestamps[0],
                'last_attempt': timestamps[-1]
            })
    
    return alerts
```

## Example: Tracking Privileged Operations

```python
def audit_api_key_operations(log_file='logs/audit.log'):
    """Track all API key management operations"""
    events = []
    
    with open(log_file, 'r') as f:
        for line in f:
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                event = json.loads(parts[3].strip())
                if event['event_type'] in ['api_key:created', 'api_key:deleted', 'api_key:revoked']:
                    events.append(event)
    
    return events
```

## Testing Audit Logging

Comprehensive test suite in `tests/test_audit_logging.py`:

```bash
# Run audit logging tests
python -m pytest tests/test_audit_logging.py -v

# Test specific functionality
python -m pytest tests/test_audit_logging.py::test_user_registration_audit_log -v
python -m pytest tests/test_audit_logging.py::test_user_login_success_audit_log -v
python -m pytest tests/test_audit_logging.py::test_user_login_failed_audit_log -v
```

### Test Coverage

- Audit event creation and serialization
- User registration logging
- Login success/failure logging
- API key operations logging
- Event data structure and required fields
- Timestamp and source IP tracking
- Special character handling in event details
- Event severity levels
- Edge cases with missing optional fields

## Configuration

Modify audit logging in `app/audit_logger.py`:

```python
# Change log file location
handler = logging.FileHandler("logs/audit.log")

# Change logger name
logger = logging.getLogger("custom.audit.logger")

# Add custom formatters
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
```

## Performance Impact

- **Memory**: ~1KB per event in memory (before write)
- **CPU**: < 1% overhead (minimal JSON serialization)
- **Disk**: ~500 bytes per event (typical log entry)
- **Latency**: < 1ms per audit log call (file I/O handled by OS buffer)

For typical usage (100 logins/hour):
```
Disk/Hour: ~50 KB
Disk/Day: ~1.2 MB
Disk/Month: ~36 MB
```

## Compliance

Audit logging helps meet security compliance requirements:

- **OWASP**: Implements proper logging and monitoring (A09:2021)
- **NIST SP 800-53**: Provides audit trail for account access (AC-2, AU-2)
- **PCI DSS**: Requirement 10 (logging and monitoring)
- **GDPR**: Part of security safeguards for processing records
- **SOC 2**: Type II control for access logging and monitoring
- **HIPAA**: Required for health information access tracking

## Future Enhancements

### Log Rotation

Automatically rotate and archive logs:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/audit.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10
)
```

### Centralized Logging

Send logs to external system (ELK, Splunk, etc.):

```python
import syslog

syslog_handler = logging.handlers.SysLogHandler(
    address=('logserver.example.com', 514)
)
logger.addHandler(syslog_handler)
```

### Encrypted Storage

Encrypt sensitive audit logs:

```python
from cryptography.fernet import Fernet

# Encrypt event details before logging
cipher_suite = Fernet(key)
encrypted_details = cipher_suite.encrypt(
    json.dumps(event.details).encode()
)
```

### Database Persistence

Store audit events in database for better querying:

```python
# Create AuditLog table
# Store events as database records
# Query and filter using SQLAlchemy ORM
```

### Real-time Alerting

Alert on critical security events:

```python
def alert_on_critical_events(event):
    if event['severity'] == 'critical':
        send_alert(event)  # Email, Slack, etc.
```

## Troubleshooting

**Logs not being created**
- Check `logs/` directory exists and is writable
- Verify file permissions: `chmod 755 logs/`
- Check Python logging configuration

**Logs not being written**
- Verify logger handlers are configured
- Check that log level is set to INFO or DEBUG
- Ensure audit_logger.log_event() is being called

**Performance issues**
- Consider batch writing for high volume scenarios
- Use log rotation to prevent unbounded file growth
- Consider asynchronous logging for I/O operations

## Conclusion

Audit logging is a critical security layer for HyperFactory. The structured, JSON-based approach enables:

- ✅ Transparent tracking of security-critical events
- ✅ Compliance with regulatory requirements
- ✅ Investigation of security incidents
- ✅ Monitoring of suspicious patterns
- ✅ Integration with security tools and platforms

For production deployments, strongly consider:
1. Implementing log rotation and archival
2. Setting up centralized logging (ELK, Splunk)
3. Creating automated alerts for critical events
4. Regularly reviewing and analyzing audit logs
5. Integrating with SIEM for correlation

See RATE_LIMITING.md for complementary brute-force protection and security features.
