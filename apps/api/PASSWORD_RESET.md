# Password Reset - "Forgot Password" Functionality

## Overview

HyperFactory implements secure password reset functionality using time-limited, cryptographically-signed tokens sent via email. Users can request a password reset for any account, and after verifying email access, set a new password. This enables self-service account recovery without admin intervention.

## Features

✅ **Token-Based Password Reset**
- Time-limited reset tokens (default 1 hour)
- Cryptographically signed tokens using HMAC-SHA-512
- URL-safe token encoding for email links
- Email verification as step 1 of reset

✅ **Email Workflow**
- Automated reset email generation
- Plain text and HTML email templates
- Clear reset instructions
- Secure link with expiration notice

✅ **Security**
- Short token expiration (1 hour vs 24 hours for email verification)
- One-way token verification (no database storage)
- Email address verified before accepting new password
- Audit logging of all reset attempts
- Protects against timing attacks

✅ **User Experience**
- Simple three-step process: request → verify email → set password
- Clear error messages for invalid/expired tokens
- Option to request another reset email
- Fast reset process (no waiting for admin)

✅ **Integration**
- Audit logging for security events
- Rate limiting on reset requests
- Account lockout integration (don't lockout during reset)
- Works with existing authentication system

## Architecture

### PasswordResetManager Class

Core password reset functionality:

```python
from app.password_reset import PasswordResetManager

manager = PasswordResetManager(
    secret_key="your-secret-key",
    expiration_hours=1  # Default 1 hour
)

# Request a password reset
token, user_found = manager.request_password_reset(
    db,
    email="user@example.com",
    source_ip="192.168.1.100"
)

if user_found:
    # Generate reset email with token
    reset_url = f"https://app.example.com/reset?token={token}"
    # Send email with reset_url
    pass

# Verify reset token
email = manager.verify_reset_token(token)
if email:
    # Token is valid and not expired
    pass

# Reset password
success, message = manager.reset_password(
    db,
    token=token,
    new_password="NewPassword123",
    source_ip="192.168.1.100"
)
```

### PasswordResetEmailService Class

Email generation and workflow:

```python
from app.password_reset import PasswordResetEmailService

service = PasswordResetEmailService()

# Generate plain text email
subject, body = service.generate_reset_email_body(
    username="john",
    reset_url="https://app.example.com/reset?token=abc123"
)

# Generate HTML email
html_body = service.generate_reset_email_html(
    username="john",
    reset_url="https://app.example.com/reset?token=abc123"
)

# Send email
from app.email_verification import send_verification_email

send_verification_email(
    email="user@example.com",
    subject=subject,
    body=body,
    html_body=html_body
)
```

### Global Instances

```python
from app.password_reset import password_reset_manager, PasswordResetEmailService

# Use global manager
token, found = password_reset_manager.request_password_reset(db, email)

# Use email service
service = PasswordResetEmailService()
subject, body = service.generate_reset_email_body(username, url)
```

## Password Reset Flow

```
User on Login Page
    ↓
Click "Forgot Password"
    ↓
Enter Email Address
    ↓
POST /api/auth/password-reset-request
    ├─ Rate limit check (3 requests per hour per email)
    ├─ User lookup by email
    ├─ Generate reset token (1 hour expiration)
    ├─ Send reset email
    ├─ Log event to audit log
    └─ Return success (without revealing if user exists)
       ↓
User Checks Email
    ↓
Click Reset Link
    https://app.example.com/reset?token=abc123
    ↓
Frontend Page with Password Form
    ↓
Enter New Password & Confirm
    ↓
POST /api/auth/password-reset
    ├─ Verify reset token (must not be expired)
    ├─ Extract email from token
    ├─ Validate new password
    ├─ Hash and update password in database
    ├─ Clear active sessions (optional)
    ├─ Log password change event
    └─ Return success
       ↓
Redirect to Login
    ↓
User Logs In With New Password
```

## HTTP API Endpoints (Future Implementation)

### Request Password Reset

```http
POST /api/auth/password-reset-request
Content-Type: application/json

{
  "email": "user@example.com"
}

HTTP/1.1 200 OK
{
  "message": "If an account exists, a password reset email will be sent"
}
```

**Note**: Returns same response for existing and non-existing emails to prevent email enumeration.

### Verify Reset Token

```http
GET /api/auth/password-reset-verify?token=abc123

HTTP/1.1 200 OK
{
  "valid": true,
  "email": "user@example.com"  // Optional, for UX purposes
}

HTTP/1.1 400 Bad Request
{
  "detail": "Invalid or expired reset token"
}
```

### Reset Password

```http
POST /api/auth/password-reset
Content-Type: application/json

{
  "token": "abc123",
  "password": "NewPassword123",
  "password_confirm": "NewPassword123"
}

HTTP/1.1 200 OK
{
  "message": "Password reset successfully"
}

HTTP/1.1 400 Bad Request
{
  "detail": "Invalid or expired reset token"
}
```

## Token Format

Reset tokens use `itsdangerous.TimedSerializer`:

- **Components**: Payload + timestamp + signature
- **Encoding**: URL-safe base64
- **Size**: ~200-300 bytes
- **Expiration**: 1 hour by default
- **Signing**: HMAC-SHA-512 with SECRET_KEY

### Token Example

```
eyJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20ifQ.Zfq2Lw.xyz123-abc456-def789
                    ↑                         ↑
                 Payload                  Signature
```

## Security Considerations

⚠️ **Current Implementation**

- Placeholder email sending
- 1-hour token expiration (short-lived)
- No token revocation (design choice)
- Email prevents account enumeration

✅ **Best Practices**

1. **Token Security**
   - Use strong SECRET_KEY (minimum 32 bytes)
   - Separate key from email verification if desired
   - Shorter expiration (1 hour) than email verification (24 hours)
   - Never log full tokens in debug logs

2. **Email Security**
   - Send password reset emails to account email only
   - Include user's username in email (confirms correct account)
   - Add security contact in footer
   - Don't include sensitive info in email

3. **Password Validation**
   - Enforce password strength requirements
   - Check against common passwords
   - Verify password_confirm matches password
   - Reject blank/empty passwords

4. **Account Security**
   - Optional: Clear active sessions after password reset
   - Audit log all password changes
   - Consider requiring verification email before reset
   - Support account recovery if user doesn't have email access

5. **Rate Limiting**
   - Limit password reset requests (3 per hour per email)
   - Prevent brute forcing of reset flow
   - Log repeated reset requests
   - Alert on suspicious patterns

6. **User Privacy**
   - Never confirm if email exists in system
   - Return same response for valid/invalid emails
   - Only send email to registered account
   - Allow users to safely ignore unwanted reset emails

## Configuration

### Environment Variables

```bash
# Password reset settings
PASSWORD_RESET_SECRET_KEY=your-secret-key-min-32-bytes  # Optional, defaults to SECRET_KEY
PASSWORD_RESET_EXPIRATION_HOURS=1                       # Default 1 hour

# Email service (see EMAIL_VERIFICATION.md)
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your-api-key
```

### Application Settings

Modify in `app/password_reset.py`:

```python
# Change expiration
PASSWORD_RESET_TOKEN_EXPIRATION_HOURS = 2  # 2 hours instead of 1

# Use different secret key
PASSWORD_RESET_SECRET_KEY = "your-different-secret-key"
```

## Audit Logging

Password reset events are logged with relevant details:

### Reset Request

```json
{
  "event_type": "user:password_reset",
  "action": "request",
  "severity": "info",
  "status": "success",
  "details": {
    "email": "user@example.com"
  }
}
```

### Reset Successful

```json
{
  "event_type": "user:password_changed",
  "action": "update",
  "severity": "info",
  "status": "success",
  "details": {
    "email": "user@example.com",
    "method": "password_reset"
  }
}
```

## Testing

Comprehensive test suite in `tests/test_password_reset.py`:

```bash
# Run all password reset tests
python -m pytest tests/test_password_reset.py -v

# Test specific functionality
python -m pytest tests/test_password_reset.py::test_complete_password_reset_workflow -v
```

### Test Coverage

- Token generation and verification
- Token expiration checking
- Password reset request for existing/non-existing users
- Full password reset workflow
- Email template generation
- Multiple user reset chains
- Edge cases and error handling
- Token validation and security

## Integration Examples

### Request Password Reset Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.password_reset import password_reset_manager, PasswordResetEmailService
from app.rate_limiter import check_password_reset_rate_limit, get_client_identifier
from app.email_verification import send_verification_email

@router.post("/password-reset-request")
def request_password_reset(
    email: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request a password reset for email"""
    client_ip = get_client_identifier(request)
    
    # Rate limiting: 3 password reset requests per email per hour
    check_password_reset_rate_limit(email, client_ip)
    
    # Request reset
    token, user_found = password_reset_manager.request_password_reset(
        db, email, source_ip=client_ip
    )
    
    # Send email if user found
    if token:
        reset_url = f"https://app.example.com/reset?token={token}"
        service = PasswordResetEmailService()
        
        subject, body = service.generate_reset_email_body("User", reset_url)
        html = service.generate_reset_email_html("User", reset_url)
        
        send_verification_email(email, subject, body, html)
    
    # Always return same response (don't reveal if user exists)
    return {"message": "If email exists, reset instructions will be sent"}
```

### Reset Password Endpoint

```python
@router.post("/password-reset")
def reset_password(
    token: str,
    password: str,
    password_confirm: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Reset password with reset token"""
    client_ip = get_client_identifier(request)
    
    # Validate passwords match
    if password != password_confirm:
        raise HTTPException(status_code=400, detail="Passwords don't match")
    
    # Validate password strength
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    
    # Reset password
    success, message = password_reset_manager.reset_password(
        db, token, password, source_ip=client_ip
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": "Password reset successfully. Please log in."}
```

## Compliance

Password reset helps meet security and privacy requirements:

- **OWASP**: Secure password recovery (A07:2021)
- **NIST SP 800-63**: Account recovery procedures (800-63B-5.1.4)
- **PCI DSS**: Requirement 2.3 (security procedures)
- **GDPR**: User empowerment and account control
- **SOC 2**: User access and authentication controls

## Performance Impact

- **Token Generation**: < 1ms (crypto operations)
- **Token Verification**: < 1ms (signature check)
- **Password Reset**: 100-500ms (bcrypt hashing)
- **Email Sending**: 100-5000ms (varies by provider)
- **Database**: One User update for password reset

For typical usage (50 reset requests/hour):
```
Token Operations: ~100ms per hour
Password Resets: 50-250 seconds per hour (bcrypt)
Emails: 50-250 seconds per hour (varies by provider)
```

## Future Enhancements

### Password Reset with Session Clearing

```python
def reset_password_and_clear_sessions(
    db: Session,
    token: str,
    new_password: str,
    source_ip: str = None
):
    """Reset password and invalidate all active sessions"""
    success, message = password_reset_manager.reset_password(
        db, token, new_password, source_ip=source_ip
    )
    
    if success:
        # Clear active sessions for this user
        # This would require a sessions table
        pass
    
    return success, message
```

### Email Verification Before Reset

Require additional email confirmation for high-value accounts:

```python
def reset_password_with_email_confirmation(
    db: Session,
    reset_token: str,
    confirmation_token: str,
    new_password: str
):
    """Reset password only after email confirmation"""
    # Verify both tokens
    reset_email = password_reset_manager.verify_reset_token(reset_token)
    confirm_email = email_token_manager.verify_token(confirmation_token)
    
    if reset_email == confirm_email:
        # Proceed with password reset
        pass
```

### Password Reset via SMS

Provide SMS-based reset for mobile users:

```python
def request_sms_password_reset(db: Session, phone: str):
    """Request password reset via SMS"""
    # Generate token
    token = password_reset_manager.generate_reset_token(...)
    
    # Send SMS with reset link
    send_sms(phone, f"Reset password: https://app.example.com/reset?token={token}")
```

## Troubleshooting

**Reset token keeps expiring**
- Verify token expiration is set correctly (1 hour default)
- Check system clock synchronization
- Confirm TIMESTAMP generation is working

**Password reset emails not being sent**
- Verify email provider configuration (see EMAIL_VERIFICATION.md)
- Check send_verification_email() implementation
- Monitor email service logs for failures

**Users getting locked out after reset**
- Ensure account_lockout_manager doesn't lock during reset
- Reset should clear failed login attempts
- Verify new password is being validated correctly

**Reset link not working**
- Ensure full URL is included in email
- Verify domain routing is correct
- Check token format in URL (no encoding issues)
- Test token verification locally

## Conclusion

Password reset is a critical feature for self-service account recovery that:

- ✅ Enables users to regain access without support
- ✅ Reduces support burden
- ✅ Maintains security with time-limited tokens
- ✅ Prevents account enumeration attacks
- ✅ Integrates with audit logging
- ✅ Complies with regulations

For production deployments, ensure:
1. Email provider integration
2. Rate limiting configuration
3. Strong SECRET_KEY and environment setup
4. Audit logging monitoring
5. User communication and support

See RATE_LIMITING.md, AUDIT_LOGGING.md, and EMAIL_VERIFICATION.md for complementary features.
