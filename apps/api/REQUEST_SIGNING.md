# Request Signing - Cryptographic Request Authentication and Integrity Verification

## Overview

HyperFactory implements cryptographic request signing using HMAC-SHA256 to provide:

1. **Authentication**: Verify requests come from the legitimate API key holder
2. **Integrity**: Detect any tampering with the request body
3. **Replay Protection**: Prevent old requests from being replayed
4. **Idempotency**: Support safe request retries with nonces

This layer works alongside API Key Scoping to provide comprehensive API security. While scopes control *what* an API key can do, request signing verifies *who* is making the request and that the request hasn't been modified.

## Features

✅ **HMAC-SHA256 Signing**
- Industry-standard cryptographic signing algorithm
- Timing-attack resistant verification
- Deterministic signature generation

✅ **Request Integrity**
- Detects any modification to request body
- Works with JSON, form data, and binary payloads
- Prevents man-in-the-middle attacks

✅ **Replay Protection**
- Timestamp validation (configurable window, default 5 minutes)
- Prevents old requests from being replayed
- Clock skew tolerance

✅ **Idempotency Support**
- Nonce/request ID for idempotent requests
- Detect duplicate requests
- Safe retry semantics

✅ **Audit Logging**
- Log all signature verification attempts
- Security monitoring and compliance
- SIEM integration ready

✅ **Flexible Configuration**
- Configurable timestamp max age
- Support for both timestamped and nonce-based approaches
- Version-aware signature format

## Architecture

### Security Model

```
Client Side:
1. Generate timestamp (ISO 8601)
2. Optionally generate nonce (random hex)
3. Create signing string: "timestamp:nonce:body" or "timestamp:body"
4. Sign with HMAC-SHA256(api_secret, signing_string)
5. Include headers: X-Timestamp, X-Nonce (optional), X-Signature

Server Side:
1. Extract headers: X-Timestamp, X-Nonce (optional), X-Signature
2. Validate timestamp freshness (prevent replay)
3. Validate nonce (optional, for idempotency)
4. Regenerate signature with same inputs
5. Compare signatures (constant-time comparison)
6. Grant/deny request based on result
```

### Signature Format

```
X-Signature: 1:abc123def456...

Version 1:
- Timestamp-based signing string
- HMAC-SHA256 output as hex
- Nonce support (optional)
```

### Signing String Construction

With nonce:
```
"2024-01-15T10:30:45.123456:abc123def456:{"user":"test"}"
```

Without nonce:
```
"2024-01-15T10:30:45.123456:{"user":"test"}"
```

## Core Classes

### RequestSigningManager

Main class for signature generation and verification.

#### Static Methods

**generate_signature(api_key_secret: str, request_body: bytes, timestamp: str, nonce: Optional[str]) → str**

Generate HMAC-SHA256 signature for request:

```python
from app.request_signing import RequestSigningManager
from datetime import datetime

# Generate signature
signature = RequestSigningManager.generate_signature(
    api_key_secret="sk_abc123xyz789...",
    request_body=b'{"action": "create", "data": {...}}',
    timestamp=datetime.utcnow().isoformat(),
    nonce=None  # Optional
)
# Returns: "1:abc123def456..."
```

**verify_signature(api_key_secret: str, request_body: bytes, signature: str, timestamp: str, nonce: Optional[str]) → bool**

Verify HMAC-SHA256 signature for request:

```python
# Verify signature
is_valid = RequestSigningManager.verify_signature(
    api_key_secret="sk_abc123xyz789...",
    request_body=request.body,
    signature=request.headers.get("X-Signature"),
    timestamp=request.headers.get("X-Timestamp"),
    nonce=request.headers.get("X-Nonce")
)

if is_valid:
    # Process request
    pass
else:
    # Reject with 401 Unauthorized
    pass
```

#### Instance Methods

**validate_timestamp(timestamp: str, max_age_seconds: Optional[int]) → Tuple[bool, Optional[str]]**

Validate timestamp freshness (prevent replay):

```python
manager = RequestSigningManager(timestamp_max_age_seconds=300)  # 5 minutes

# Validate client's timestamp
is_valid, error = manager.validate_timestamp(
    request.headers.get("X-Timestamp")
)

if not is_valid:
    # Reject: timestamp too old or in future
    return error_response(401, error)
```

**validate_nonce(nonce: str, max_age_seconds: int) → Tuple[bool, Optional[str]]**

Validate nonce format and freshness:

```python
manager = RequestSigningManager()

# Validate nonce for idempotency
is_valid, error = manager.validate_nonce(
    request.headers.get("X-Nonce"),
    max_age_seconds=86400  # 24 hours
)

if not is_valid:
    return error_response(400, error)

# Check nonce storage (deduplication requires external storage)
if request_already_processed(nonce):
    return existing_response  # Return cached response
```

**generate_nonce() → str**

Generate random nonce for idempotent requests:

```python
nonce = RequestSigningManager.generate_nonce()
# Returns: 64-character hex string
```

**extract_signature_components(signature_header, timestamp_header, nonce_header) → Tuple**

Extract and validate headers in one call:

```python
manager = RequestSigningManager()

sig, ts, nonce, error = manager.extract_signature_components(
    request.headers.get("X-Signature"),
    request.headers.get("X-Timestamp"),
    request.headers.get("X-Nonce")
)

if error:
    return error_response(400, error)

# Components validated and ready to use
```

**log_signature_verification(api_key_id, is_valid, error, request_path, source_ip)**

Log signature verification attempts for auditing:

```python
manager = RequestSigningManager()

manager.log_signature_verification(
    api_key_id="key_abc123",
    is_valid=True,
    request_path="/api/factories",
    source_ip="192.168.1.1"
)
```

## HTTP Headers

### Required Headers

**X-Signature**
- HMAC-SHA256 signature of request
- Format: "1:hexhexhex..."
- Example: `X-Signature: 1:abc123def456789...`

**X-Timestamp**
- ISO 8601 timestamp of request
- Must be within configured window (default ±5 minutes)
- Example: `X-Timestamp: 2024-01-15T10:30:45.123456`

### Optional Headers

**X-Nonce**
- Unique request ID for idempotency
- 16-128 character hex string
- Example: `X-Nonce: abc123def456789012345...`

### Example Request

```
POST /api/factories HTTP/1.1
Host: api.hyperfactory.com
Content-Type: application/json
Authorization: Bearer key_abc123
X-Timestamp: 2024-01-15T10:30:45.123456
X-Nonce: abc123def456789012345def456789ab
X-Signature: 1:abc123def456789012345def456789abc123def456789012345def456789abcd

{
  "name": "Factory A",
  "location": "San Francisco"
}
```

## Integration Examples

### FastAPI Middleware

```python
from fastapi import FastAPI, HTTPException, Request
from app.request_signing import request_signing_manager
from app.models import APIKey
from sqlalchemy.orm import Session

app = FastAPI()

@app.middleware("http")
async def verify_request_signature(request: Request, call_next):
    """Middleware to verify request signatures"""
    
    # Skip signature verification for certain endpoints
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # Extract headers
    api_key_id = request.headers.get("Authorization", "").replace("Bearer ", "")
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    
    if not api_key_id or not signature:
        raise HTTPException(status_code=401, detail="Missing API key or signature")
    
    # Validate components
    sig, ts, n, error = request_signing_manager.extract_signature_components(
        signature, timestamp, nonce
    )
    if error:
        raise HTTPException(status_code=400, detail=f"Invalid headers: {error}")
    
    # Get API key from database
    db = get_db()  # dependency injection
    api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Read request body
    body = await request.body()
    
    # Verify signature
    is_valid = request_signing_manager.verify_signature(
        api_key.secret,
        body,
        signature,
        timestamp,
        nonce
    )
    
    if not is_valid:
        request_signing_manager.log_signature_verification(
            api_key_id=api_key_id,
            is_valid=False,
            error="Signature verification failed",
            request_path=request.url.path,
            source_ip=request.client.host
        )
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Log successful verification
    request_signing_manager.log_signature_verification(
        api_key_id=api_key_id,
        is_valid=True,
        request_path=request.url.path,
        source_ip=request.client.host
    )
    
    # Continue processing
    response = await call_next(request)
    return response
```

### Client Library (Python)

```python
import requests
import hmac
import hashlib
from datetime import datetime

class HyperFactoryClient:
    """Client for HyperFactory API with request signing"""
    
    def __init__(self, api_key_id: str, api_key_secret: str, base_url: str):
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.base_url = base_url
    
    def _sign_request(self, body: bytes, timestamp: str, nonce: str = None) -> str:
        """Generate HMAC-SHA256 signature"""
        if nonce:
            signing_string = f"{timestamp}:{nonce}:{body.decode('utf-8')}"
        else:
            signing_string = f"{timestamp}:{body.decode('utf-8')}"
        
        sig_hex = hmac.new(
            self.api_key_secret.encode(),
            signing_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"1:{sig_hex}"
    
    def post(self, path: str, data: dict, idempotent: bool = False):
        """Make signed POST request"""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode('utf-8')
        timestamp = datetime.utcnow().isoformat()
        
        # Generate nonce for idempotent requests
        nonce = None
        if idempotent:
            nonce = secrets.token_hex(32)
        
        # Sign request
        signature = self._sign_request(body, timestamp, nonce)
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self.api_key_id}",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }
        if nonce:
            headers["X-Nonce"] = nonce
        
        # Make request
        response = requests.post(url, data=body, headers=headers)
        return response

# Usage
client = HyperFactoryClient(
    api_key_id="key_abc123",
    api_key_secret="sk_xyz789...",
    base_url="https://api.hyperfactory.com"
)

response = client.post("/api/factories", {
    "name": "Factory A",
    "location": "San Francisco"
})
```

### JavaScript/Node.js Client

```javascript
const crypto = require('crypto');
const axios = require('axios');

class HyperFactoryClient {
    constructor(apiKeyId, apiKeySecret, baseUrl) {
        this.apiKeyId = apiKeyId;
        this.apiKeySecret = apiKeySecret;
        this.baseUrl = baseUrl;
        this.client = axios.create({ baseURL: baseUrl });
    }
    
    _signRequest(body, timestamp, nonce = null) {
        let signingString = timestamp + ':';
        if (nonce) {
            signingString += nonce + ':';
        }
        signingString += body;
        
        const signature = crypto
            .createHmac('sha256', this.apiKeySecret)
            .update(signingString)
            .digest('hex');
        
        return `1:${signature}`;
    }
    
    async post(path, data, idempotent = false) {
        const body = JSON.stringify(data);
        const timestamp = new Date().toISOString();
        
        // Generate nonce for idempotent requests
        let nonce = null;
        if (idempotent) {
            nonce = crypto.randomBytes(32).toString('hex');
        }
        
        // Sign request
        const signature = this._signRequest(body, timestamp, nonce);
        
        // Prepare headers
        const headers = {
            'Authorization': `Bearer ${this.apiKeyId}`,
            'X-Timestamp': timestamp,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        };
        if (nonce) {
            headers['X-Nonce'] = nonce;
        }
        
        // Make request
        return this.client.post(path, data, { headers });
    }
}

// Usage
const client = new HyperFactoryClient(
    'key_abc123',
    'sk_xyz789...',
    'https://api.hyperfactory.com'
);

client.post('/api/factories', {
    name: 'Factory A',
    location: 'San Francisco'
});
```

## Security Best Practices

### 1. Secure Secret Storage

Store API key secrets securely:

```python
# ❌ WRONG: Hardcoded secrets
api_secret = "sk_abc123xyz789"

# ✅ CORRECT: Environment variables
import os
api_secret = os.getenv("API_KEY_SECRET")

# ✅ BETTER: Encrypted secret manager
from aws_secretsmanager import get_secret
api_secret = get_secret("hyperfactory/api/key_abc123")
```

### 2. Timestamp Validation

Always validate timestamps to prevent replay attacks:

```python
# ❌ WRONG: No timestamp validation
is_valid = verify_signature(secret, body, sig, ts)

# ✅ CORRECT: Validate timestamp first
ts_valid, ts_error = manager.validate_timestamp(ts)
if not ts_valid:
    return error(401, ts_error)

is_valid = verify_signature(secret, body, sig, ts)
```

### 3. Constant-Time Comparison

Use constant-time comparison to prevent timing attacks:

```python
# ❌ WRONG: Time-variable comparison
if calculated_sig == provided_sig:
    ...

# ✅ CORRECT: Constant-time comparison
import hmac
if hmac.compare_digest(calculated_sig, provided_sig):
    ...
```

The implementation uses `hmac.compare_digest` internally.

### 4. Nonce Deduplication

Store processed nonces to detect replays:

```python
# ❌ WRONG: No nonce storage
is_valid = verify_signature(...)

# ✅ CORRECT: Check nonce storage
if nonce_already_processed(nonce):
    return cached_response  # Idempotent

is_valid = verify_signature(...)
store_nonce(nonce)
process_request()
```

### 5. Log All Verification

Log both successful and failed signature verifications:

```python
manager.log_signature_verification(
    api_key_id=key_id,
    is_valid=is_valid,
    error=error_message,
    request_path=request.url.path,
    source_ip=request.client.host
)
```

### 6. Clock Synchronization

Ensure server clocks are synchronized (NTP):

```bash
# Check NTP status
ntpstat

# Or use systemd-timesyncd
timedatectl

# Allow 5-minute clock skew to handle drift
manager = RequestSigningManager(timestamp_max_age_seconds=300)
```

### 7. Secret Rotation

Rotate API key secrets periodically:

```python
# Create new key
new_key = create_api_key(user_id, scopes)

# Support both old and new for grace period
def verify_with_rotation(body, sig, ts, api_key_id):
    key = get_current_key(api_key_id)
    
    # Try current key
    if verify_signature(key.secret, body, sig, ts):
        return True
    
    # Try previous key (7-day grace period)
    old_key = get_previous_key(api_key_id)
    if old_key and old_key.rotated_days_ago < 7:
        if verify_signature(old_key.secret, body, sig, ts):
            return True
    
    return False

# Then deprecate old key after grace period
```

## Attack Prevention

### Replay Attack Prevention

Timestamps prevent replaying old requests:

```
Attacker intercepts: POST /transfer amount=100

Client sends again with new timestamp:
X-Timestamp: 2024-01-15T10:31:00  (different from original)
X-Signature: 1:newSignature       (must regenerate)

Server rejects: Signature mismatch
```

### Man-in-the-Middle Attack Prevention

Signature prevents MITM modification:

```
MITM intercepts: {"amount": 100}
MITM modifies to: {"amount": 1000}
MITM cannot recompute signature without secret

Server verifies:
  Computed sig (with original): valid
  Provided sig (with modified): invalid
  → Reject request
```

### Signature Forgery Prevention

Without secret, attacker cannot forge signature:

```
Attacker doesn't know secret: sk_xyz789...

Attacker tries to forge signature:
  HMAC(attacker_secret, body) ≠ HMAC(real_secret, body)

Server verification fails → Request rejected
```

## Compliance Requirements

### OWASP

- **A01:2021 - Broken Access Control**: Signature verification ensures authentic requests
- **A03:2021 - Injection**: Signature protects against request tampering
- **A05:2021 - Broken Access Control**: Prevents man-in-the-middle attacks

### NIST

- **NIST SP 800-63B**: Cryptographic verification of API requests
- **NIST SP 800-53**: SI-7 (Information System Monitoring)

### PCI DSS

- **Requirement 6.5.10**: Detect changes to API requests
- **Requirement 10**: Logging of all API signature verifications

### GDPR

- **Article 32**: Security of data in transit (signature verifies integrity)
- **Article 5**: Data protection by design

### SOC 2

- **CC6.2**: Prior to issuing security updates, systems verify source authenticity
- **CC7.2**: System monitoring of authentication attempts

## Performance Considerations

- **Signature Generation**: < 1ms (HMAC-SHA256 is fast)
- **Signature Verification**: < 1ms (cryptographic hash)
- **Timestamp Validation**: < 0.1ms (datetime parsing)
- **Overhead per Request**: < 2ms total

For typical usage (1000 req/sec):
```
Overhead: 1000 * 0.002s = 2 seconds per 1000 requests
Impact: 0.2% of throughput (negligible)
```

## Testing

Comprehensive test suite in `tests/test_request_signing.py`:

```bash
# Run all request signing tests
python3 -m pytest tests/test_request_signing.py -v

# Test specific functionality
python3 -m pytest tests/test_request_signing.py::test_verify_signature_valid -v
python3 -m pytest tests/test_request_signing.py::test_replay_attack_prevention -v

# Test coverage
python3 -m pytest tests/test_request_signing.py --cov=app.request_signing
```

### Test Coverage

- Signature generation (basic, deterministic, with nonce)
- Signature verification (valid, invalid, tampered)
- Timestamp validation (current, future, expired)
- Nonce validation (format, length, hex)
- Component extraction (headers)
- Attack prevention (replay, tampering, MITM)
- Integration flows

## Troubleshooting

### Issue: "Signature verification failed"

**Cause 1**: Clock skew
```python
# Solution: Check server and client clocks are synchronized
timedatectl
```

**Cause 2**: Wrong secret
```python
# Solution: Verify API key secret is correct
verify_key_secret(api_key_id)
```

**Cause 3**: Request body modified
```python
# Solution: Ensure request body isn't modified in middleware
# Log before/after body
```

### Issue: "Timestamp is too old"

**Cause**: Timestamp validation window too strict

**Solution**:
```python
# Increase timestamp max age
manager = RequestSigningManager(timestamp_max_age_seconds=600)  # 10 minutes
```

### Issue: "Invalid nonce format"

**Cause**: Nonce not valid hex

**Solution**:
```python
# Generate valid nonce
nonce = RequestSigningManager.generate_nonce()
# Returns 64-char hex string
```

### Issue: Timing attacks suspected

**Cause**: Using `==` instead of `hmac.compare_digest`

**Solution**:
```python
# Use constant-time comparison (built-in)
is_valid = RequestSigningManager.verify_signature(...)
# Already uses hmac.compare_digest internally
```

## Future Enhancements

### Algorithm Flexibility

```python
# Support multiple signature algorithms
ALGORITHMS = {
    "HMAC-SHA256": "default_v1",
    "HMAC-SHA512": "v2",
    "RSA-SHA256": "asymmetric_v1"
}
```

### Mutual TLS (mTLS)

```python
# Combine with mTLS for additional security
import ssl
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.load_cert_chain("client.crt", "client.key")
```

### Key Rotation Automation

```python
# Automatic key rotation with grace period
@scheduled_task(frequency="weekly")
def rotate_api_keys():
    # Create new key
    # Set grace period (7 days)
    # Schedule old key deletion
```

### Signature Headers Encryption

```python
# Encrypt signature header in transit
X-Signature: eyJh... (encrypted)
X-Signature-Key-ID: key_123
```

## Conclusion

Request Signing provides critical API security:

- ✅ Authenticates request origin (who)
- ✅ Verifies request integrity (what)
- ✅ Prevents replay attacks (when)
- ✅ Supports safe retries (idempotency)

Combined with API Key Scoping, provides comprehensive API access control:
- Scoping: What the key can do (fine-grained permissions)
- Signing: Who is making the request (cryptographic authentication)

For production deployment:
1. Implement request signing middleware
2. Validate timestamps (prevent replay)
3. Store nonces for idempotency
4. Log all verification attempts
5. Educate clients on implementation
6. Rotate secrets regularly
7. Monitor signature failures
8. Integrate with SIEM systems

See API_KEY_SCOPING.md, AUDIT_LOGGING.md, and SESSION_MANAGEMENT.md for complementary security features.
