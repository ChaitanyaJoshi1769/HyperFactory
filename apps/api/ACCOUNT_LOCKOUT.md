# Account Lockout - Brute-Force Protection

## Overview

HyperFactory implements automatic account lockout to protect against brute-force login attacks. After a configurable number of failed login attempts, user accounts are automatically locked for a specified duration. This mechanism works in conjunction with rate limiting to provide multi-layered protection.

## Features

✅ **Automatic Account Lockout**
- Lock accounts after 5 failed login attempts (configurable)
- Automatic unlock after 30 minutes (configurable)
- Prevents further login attempts during lockout

✅ **Integrated Protection**
- Works alongside rate limiting for request-level protection
- Rate limiting blocks requests early
- Account lockout provides account-level protection
- Layered defense against sophisticated brute-force attacks

✅ **User Feedback**
- Clear error messages indicating account is locked
- Displays remaining lockout time
- Distinct error codes (403 Forbidden vs 401 Unauthorized)

✅ **Audit Logging**
- Log all account lockout events with severity CRITICAL
- Track lockout reasons and duration
- Records source IP for lockout events
- Enables security monitoring and incident investigation

✅ **Automatic Unlock**
- Accounts automatically unlock when timeout expires
- No manual admin intervention required for normal cases
- Verified on each login attempt

## Architecture

### AccountLockoutManager Class

Core lockout management logic:

```python
from app.account_lockout import AccountLockoutManager

# Create with custom settings
manager = AccountLockoutManager(
    max_failed_attempts=5,
    lockout_duration_minutes=30
)

# Check if account is locked (auto-unlocks if timeout expired)
is_locked = manager.is_account_locked(db, user_id)

# Lock an account
manager.lock_account(
    db,
    user,
    source_ip="192.168.1.100",
    reason="too_many_failed_attempts"
)

# Unlock an account
manager.unlock_account(db, user_id)

# Record failed login and lock if threshold exceeded
was_locked = manager.record_failed_login(
    db,
    user,
    failed_attempts=5,
    source_ip="192.168.1.100"
)

# Get detailed lockout status
status = manager.get_lockout_status(db, user_id)
# Returns: {
#   "locked": False
# } OR {
#   "locked": True,
#   "locked_until": "2026-05-25T11:30:45.123456",
#   "seconds_remaining": 1245
# }
```

### Global Lockout Manager Instance

The module provides a global lockout manager instance:

```python
from app.account_lockout import account_lockout_manager

# Check if account is locked
if account_lockout_manager.is_account_locked(db, user_id):
    # Block login attempt
    pass
```

### User Model Extensions

The User model includes lockout fields:

```python
class User(Base):
    __tablename__ = "users"

    # ... existing fields ...

    is_locked = Column(Boolean, default=False, index=True)
    locked_until = Column(DateTime)  # Auto-unlock timestamp
```

## Integration with Login Endpoint

Account lockout is integrated into the authentication flow:

```python
@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login user and get access token"""
    client_ip = get_client_identifier(request)

    # 1. Check rate limit (request-level)
    check_login_rate_limit(credentials.username, client_ip)

    # 2. Check if account is locked (account-level)
    user = db.query(User).filter(User.username == credentials.username).first()
    if user and account_lockout_manager.is_account_locked(db, str(user.id)):
        lockout_status = account_lockout_manager.get_lockout_status(db, str(user.id))
        raise HTTPException(
            status_code=403,  # Forbidden, not Unauthorized
            detail=f"Account is locked. Try again in {status['seconds_remaining']} seconds."
        )

    # 3. Authenticate user
    authenticated_user = AuthService.authenticate_user(db, credentials)

    if not authenticated_user:
        # Record failed attempt and lock if threshold exceeded
        if user:
            failed_attempts = get_failed_attempt_count(credentials.username)
            account_lockout_manager.record_failed_login(
                db, user, failed_attempts, source_ip=client_ip
            )

        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 4. Login successful
    access_token = AuthService.create_access_token_for_user(user, ...)
    return TokenResponse(access_token=access_token, ...)
```

## Login Flow with Protection

```
Client Login Attempt
    ↓
Check Rate Limit (1 request/user over time)
    ├─ BLOCKED → 429 Too Many Requests
    └─ ALLOWED
       ↓
Check Account Lockout (account-level)
    ├─ LOCKED → 403 Account Locked
    └─ UNLOCKED
       ↓
Authenticate (username/password)
    ├─ FAILED → Increment failed attempts
    │           Lock if threshold exceeded
    │           → 401 Invalid Credentials
    └─ SUCCESS → Login & issue token
                 → 200 OK with JWT
```

## Configuration

### Default Settings

- **max_failed_attempts**: 5 attempts before lockout
- **lockout_duration_minutes**: 30 minutes lockout

### Customization

Modify in `app/account_lockout.py`:

```python
# Use stricter settings
account_lockout_manager = AccountLockoutManager(
    max_failed_attempts=3,        # Lock after 3 attempts
    lockout_duration_minutes=60   # Lock for 1 hour
)
```

Or programmatically:

```python
from app.account_lockout import account_lockout_manager

# Change configuration
account_lockout_manager.max_failed_attempts = 10
account_lockout_manager.lockout_duration_minutes = 15
```

## HTTP Response Status Codes

The login endpoint now returns different status codes for different failure scenarios:

- **200 OK**: Successful login with token
- **401 Unauthorized**: Invalid credentials, user doesn't exist
- **403 Forbidden**: Account is locked due to failed attempts
- **429 Too Many Requests**: Rate limit exceeded (request level)

### Example Responses

**Account Locked:**
```json
HTTP/1.1 403 Forbidden
{
  "detail": "Account is locked. Try again in 1245 seconds."
}
```

**Invalid Credentials:**
```json
HTTP/1.1 401 Unauthorized
{
  "detail": "Invalid username or password"
}
```

**Rate Limited:**
```json
HTTP/1.1 429 Too Many Requests
{
  "detail": "Too many attempts. Try again in 245 seconds."
}
Retry-After: 245
```

## Audit Logging

Account lockout events are logged as CRITICAL severity:

```json
{
  "timestamp": "2026-05-25T11:00:00.123456",
  "event_type": "security:account_lockout",
  "actor_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "resource_type": "user",
  "action": "lock",
  "severity": "critical",
  "details": {
    "username": "john@example.com",
    "reason": "too_many_failed_attempts (5)",
    "locked_until": "2026-05-25T11:30:45.123456"
  },
  "source_ip": "192.168.1.100",
  "status": "success"
}
```

Failed login attempts on locked accounts are logged separately:

```json
{
  "event_type": "user:login_failed",
  "details": {
    "username": "john@example.com",
    "reason": "account_locked"
  }
}
```

## Security Considerations

⚠️ **Current Implementation**

- Lockout state stored in database
- Auto-unlock based on timestamp comparison
- Client IP tracked for forensics
- No distributed lockout across multiple servers

✅ **Best Practices**

1. **Lockout Duration**
   - 30 minutes recommended for most deployments
   - Shorter (15 min) for high-security environments
   - Longer (60+ min) only if admin unlock is unavailable

2. **Failure Threshold**
   - 5 attempts recommended (balances usability vs security)
   - 3 attempts for high-security environments
   - 10+ attempts only if accepting higher attack risk

3. **Monitoring**
   - Alert on lockouts from unusual locations
   - Monitor for patterns of lockouts from same IP
   - Review audit logs regularly for attack patterns

4. **User Communication**
   - Send email notifications for account lockouts
   - Include locked_until timestamp in notifications
   - Provide support contact information

5. **Admin Unlock**
   - Implement admin interface to manually unlock accounts
   - Log all manual unlocks with admin ID
   - Require strong authentication for admin actions

6. **Multi-Server Deployments**
   - Consider distributed lockout with Redis/cache
   - Sync lockout state across servers
   - Ensure consistent failure counting across instances

## Testing

Comprehensive test suite in `tests/test_account_lockout.py`:

```bash
# Run account lockout tests
python -m pytest tests/test_account_lockout.py -v

# Test specific scenarios
python -m pytest tests/test_account_lockout.py::test_account_lockout_after_failed_logins -v
python -m pytest tests/test_account_lockout.py::test_account_auto_unlock_after_timeout -v
```

### Test Coverage

- Account lockout manager creation
- Lock and unlock operations
- Automatic unlock after timeout
- Lockout status queries
- Failed login recording and threshold checking
- Login endpoint integration
- Locked account login attempts
- Audit logging for lockouts
- Edge cases and error handling
- Multiple lockout/unlock cycles

## Examples

### Admin Unlock Endpoint (Future Enhancement)

```python
@router.post("/admin/users/{user_id}/unlock", tags=["admin"])
def admin_unlock_user(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Admin endpoint to manually unlock a user account"""
    # Verify admin permissions
    admin = AuthService.verify_user_token(credentials.credentials)
    admin_user = AuthService.get_user(db, admin)
    if not admin_user or not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Unlock account
    from uuid import UUID
    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    account_lockout_manager.unlock_account(db, user_id)

    # Audit log
    client_ip = get_client_identifier(request) if request else None
    audit_logger.log_event(
        event_type="security:account_unlock",
        actor_id=str(admin),
        resource_id=user_id,
        resource_type="user",
        action="unlock",
        severity=AuditEventSeverity.WARNING,
        details={"unlocked_user": user.username},
        source_ip=client_ip
    )

    return {"message": f"User {user.username} has been unlocked"}
```

### Monitoring Script

```python
def get_locked_accounts(db: Session) -> list:
    """Get all currently locked accounts"""
    from app.models import User
    locked_users = db.query(User).filter(User.is_locked == True).all()
    
    results = []
    for user in locked_users:
        status = account_lockout_manager.get_lockout_status(db, str(user.id))
        results.append({
            "username": user.username,
            "locked_until": status.get("locked_until"),
            "seconds_remaining": status.get("seconds_remaining")
        })
    
    return results

def detect_lockout_patterns(log_file='logs/audit.log') -> dict:
    """Detect suspicious lockout patterns"""
    import json
    from collections import defaultdict
    
    ip_lockouts = defaultdict(list)
    user_lockouts = defaultdict(list)
    
    with open(log_file, 'r') as f:
        for line in f:
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                event = json.loads(parts[3].strip())
                if event.get('event_type') == 'security:account_lockout':
                    ip = event.get('source_ip')
                    username = event.get('details', {}).get('username')
                    
                    if ip:
                        ip_lockouts[ip].append(event)
                    if username:
                        user_lockouts[username].append(event)
    
    # Detect suspicious patterns
    alerts = []
    
    # IPs with multiple lockouts
    for ip, events in ip_lockouts.items():
        if len(events) > 5:
            alerts.append({
                'type': 'suspicious_ip',
                'ip': ip,
                'lockout_count': len(events)
            })
    
    # Users with multiple lockouts
    for username, events in user_lockouts.items():
        if len(events) > 2:
            alerts.append({
                'type': 'repeated_lockout',
                'username': username,
                'lockout_count': len(events)
            })
    
    return alerts
```

## Compliance

Account lockout helps meet security compliance requirements:

- **OWASP**: Protection against brute force attacks (A07:2021)
- **NIST SP 800-63**: Account lockout policy (800-63B-5.2.2)
- **PCI DSS**: Requirement 8.5.5 (restrict access attempts)
- **GDPR**: Security safeguards for personal data
- **SOC 2**: Control for preventing unauthorized access

## Performance Impact

- **Database**: One query to check/update is_locked and locked_until
- **CPU**: Minimal (timestamp comparison)
- **Latency**: < 1ms per login (database lookup)

For typical usage (100 logins/hour):
```
Database Queries/Hour: 100 lockout checks
Storage: ~100 bytes per user (is_locked + locked_until)
```

## Future Enhancements

### IP-Based Lockout

Block IPs after multiple failed attempts across different accounts:

```python
class IPBasedLockout:
    def __init__(self, max_attempts_per_ip=20, lockout_duration=3600):
        self.ip_attempts = {}  # {ip: [timestamps]}
        self.locked_ips = {}   # {ip: locked_until}
    
    def is_ip_locked(self, ip: str) -> bool:
        if ip in self.locked_ips:
            if datetime.utcnow() < self.locked_ips[ip]:
                return True
            else:
                del self.locked_ips[ip]
        return False
    
    def record_failure(self, ip: str) -> bool:
        if ip not in self.ip_attempts:
            self.ip_attempts[ip] = []
        
        self.ip_attempts[ip].append(datetime.utcnow())
        recent = [t for t in self.ip_attempts[ip] 
                  if datetime.utcnow() - t < timedelta(hours=1)]
        
        if len(recent) > self.max_attempts_per_ip:
            self.locked_ips[ip] = datetime.utcnow() + timedelta(
                seconds=self.lockout_duration
            )
            return True
        
        return False
```

### Email Notifications

Notify users of account lockouts:

```python
def send_lockout_notification(user: User, locked_until: datetime):
    """Send email notification of account lockout"""
    from app.mail import send_email
    
    send_email(
        to=user.email,
        subject="Your account has been locked",
        body=f"""
        Your account has been locked due to multiple failed login attempts.
        
        Account will be automatically unlocked at: {locked_until}
        
        If you didn't attempt this login, your account may be compromised.
        Please contact support immediately.
        """
    )
```

### Graduated Response

Increase restrictions based on lockout frequency:

```python
def get_lockout_multiplier(user: User) -> int:
    """Increase lockout duration for repeated offenses"""
    lockout_count = count_recent_lockouts(user.id, days=30)
    
    return 1 * (2 ** lockout_count)  # 1x, 2x, 4x, 8x, etc.
```

## Troubleshooting

**Accounts getting locked too frequently**
- Increase `max_failed_attempts` in configuration
- Check for issues with password hashing validation
- Monitor for coordinated attacks from shared networks

**Accounts not auto-unlocking**
- Verify database timestamp is UTC
- Check for timezone conversion issues
- Ensure `locked_until` is being set correctly

**Rate limiting blocking before lockout**
- Rate limiting (429) hits before lockout (403)
- This is expected - rate limiting is faster check
- Accounts still lock if they continue past rate limit

## Conclusion

Account lockout provides critical protection against brute-force attacks by automatically disabling accounts after repeated failed login attempts. Combined with rate limiting, it creates a multi-layered defense:

- **Rate Limiting**: Blocks high-frequency requests early (429)
- **Account Lockout**: Prevents further attempts on compromised accounts (403)
- **Audit Logging**: Tracks all security events for forensics

See RATE_LIMITING.md and AUDIT_LOGGING.md for complementary security features.
