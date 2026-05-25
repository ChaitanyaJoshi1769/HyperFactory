# Rate Limiting - API Abuse Prevention and Traffic Control

## Overview

Rate limiting is a critical security and stability mechanism that protects APIs from abuse, prevents resource exhaustion, and ensures fair access for all users. HyperFactory implements three distinct rate-limiting strategies, each with different trade-offs between accuracy, memory usage, and performance.

### Key Features

- **Multiple Strategies**: Fixed Window, Sliding Window, and Token Bucket algorithms
- **Flexible Configuration**: Per-minute, per-hour, and per-day limits
- **Burst Allowance**: Controlled burst support for temporary traffic spikes
- **Comprehensive Tracking**: Request counting and usage statistics
- **Security Audit Logging**: Full request tracing for security analysis
- **Production Ready**: Pre-configured limiters for authentication endpoints

## Architecture

### Rate Limiting Strategies

#### 1. Fixed Window (FIXED_WINDOW)

**Simplest, least accurate, but lowest overhead**

- Divides time into fixed windows (minute, hour, day)
- Counts requests in each window independently
- Resets at fixed time boundaries (e.g., every minute)

**Characteristics:**
- Memory: O(1) per identifier (constant)
- CPU: O(1) check (very fast)
- Accuracy: Low - boundary condition issues
- Burst handling: Poor - allows spike at window boundaries

**Use Cases:**
- High-volume APIs where accuracy is less critical
- Simple rate limiting for public endpoints
- Scenarios where memory efficiency is paramount

#### 2. Sliding Window (SLIDING_WINDOW)

**Most accurate, moderate overhead, best for most use cases**

- Maintains request history within rolling time windows
- Counts requests in a continuous rolling window
- More accurate than fixed window with reasonable memory usage

**Characteristics:**
- Memory: O(n) where n = requests in window (typical: small)
- CPU: O(n) check (still fast for typical request rates)
- Accuracy: High - prevents boundary bursts
- Burst handling: Good - enforces limits across time

**Use Cases:**
- Standard rate limiting for APIs
- Per-user or per-API-key rate limiting
- Scenarios where accuracy matters but memory is available

#### 3. Token Bucket (TOKEN_BUCKET)

**Fairest, allows controlled bursts, best for mixed traffic**

- Replenishes tokens at a fixed rate
- Allows burst up to bucket capacity
- Common in production systems

**Characteristics:**
- Memory: O(1) per identifier (constant, just stores token count)
- CPU: O(1) check (very fast)
- Accuracy: Medium - doesn't track individual requests
- Burst handling: Excellent - controlled burst support

**Use Cases:**
- APIs that tolerate bursts but need fair long-term limits
- Services with variable load patterns
- Scenarios where request patterns are bursty but bounded

## Configuration

### RateLimitConfig Class

```python
from app.rate_limiter import RateLimitConfig

# Default configuration
config = RateLimitConfig()

# Custom configuration
config = RateLimitConfig(
    requests_per_minute=50,    # Default: 100
    requests_per_hour=1000,    # Default: 3000
    requests_per_day=10000,    # Default: 50000
    burst_allowance=1.5        # Default: 1.5
)
```

**Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `requests_per_minute` | int | 100 | Requests allowed per minute |
| `requests_per_hour` | int | 3000 | Requests allowed per hour |
| `requests_per_day` | int | 50000 | Requests allowed per day |
| `burst_allowance` | float | 1.5 | Multiplier for token bucket burst (1.0 = no burst) |

### RateLimitStatus Class

Returned by rate limiter checks, contains decision and response headers:

```python
from app.rate_limiter import RateLimitStatus

status = RateLimitStatus(
    allowed=True,                          # Is request allowed?
    requests_remaining=95,                 # Remaining requests in window
    reset_at=datetime(2026, 5, 25, 10, 31, 0),  # When window resets
    retry_after_seconds=None               # Seconds until can retry (if denied)
)

# Convert to HTTP response headers
headers = status.to_headers()
# Returns: {
#     'X-RateLimit-Remaining': '95',
#     'X-RateLimit-Reset': '1749432660'  (Unix timestamp)
# }
```

## RateLimiter API

### Creating Limiters

```python
from app.rate_limiter import RateLimiter, RateLimitStrategy, RateLimitConfig

# Using default strategy (Fixed Window)
limiter = RateLimiter()

# Using specific strategy
fixed = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
sliding = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
token = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
```

### Checking Rate Limits

```python
config = RateLimitConfig(requests_per_minute=10)
now = datetime.utcnow()

# Check if request is allowed
status = limiter.check_limit("user_123", config, now)

if status.allowed:
    # Process request
    response_headers = status.to_headers()
else:
    # Return 429 Too Many Requests
    retry_after = status.retry_after_seconds
    return Response(
        "Rate limit exceeded",
        status_code=429,
        headers={
            'Retry-After': str(retry_after),
            **status.to_headers()
        }
    )
```

### Getting Usage Statistics

```python
# Get usage for identifier
usage = limiter.get_usage("user_123")

# Sliding window returns:
# {
#     "requests_last_minute": 7,
#     "requests_last_hour": 150,
#     "requests_last_day": 2000,
#     "total_requests": 2000
# }

# Token bucket returns:
# {
#     "tokens_available": 3,
#     "last_refill": "2026-05-25T10:30:00"
# }
```

### Resetting Limits

```python
# Reset for single identifier
limiter.reset("user_123")

# Reset for all identifiers
limiter.reset_all()
```

## Pre-Configured Limiters for Authentication

The rate limiter module includes pre-configured limiters for common authentication scenarios:

```python
from app.rate_limiter import (
    login_limiter,
    register_limiter,
    get_client_identifier,
    check_login_rate_limit,
    check_register_rate_limit,
)

# Helper function to get client identifier
def rate_limit_login(request):
    client_id = get_client_identifier(request)
    allowed, error = check_login_rate_limit(client_id)
    if not allowed:
        return {"error": error}, 429

def rate_limit_register(request):
    client_id = get_client_identifier(request)
    allowed, error = check_register_rate_limit(client_id)
    if not allowed:
        return {"error": error}, 429
```

**Client Identifier Logic:**

```python
def get_client_identifier(request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses X-Forwarded-For header for load balancer scenarios,
    falls back to client IP address.
    """
    # Check for proxy header (load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Use direct client IP
    return request.client.host
```

## HTTP Headers

Rate limiting uses standard HTTP headers for client communication:

### Response Headers (All Requests)

```
X-RateLimit-Remaining: 95        # Requests remaining in window
X-RateLimit-Reset: 1749432660    # Unix timestamp when limit resets
```

### Response Headers (Denied Requests Only)

```
HTTP/1.1 429 Too Many Requests
Retry-After: 45                   # Seconds until can retry
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1749432660
```

## FastAPI Middleware Integration

### Complete Middleware Example

```python
from fastapi import Request, Response
from app.rate_limiter import (
    rate_limiter,
    RateLimitConfig,
    get_client_identifier,
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Apply rate limiting to all requests.
    Exempts certain paths from rate limiting.
    """
    # Exempt health checks and public endpoints
    exempt_paths = {"/health", "/api/status", "/docs", "/openapi.json"}
    if request.url.path in exempt_paths:
        return await call_next(request)
    
    # Get rate limit configuration based on path
    if request.url.path.startswith("/api/auth/login"):
        config = LOGIN_RATE_LIMIT_CONFIG
    elif request.url.path.startswith("/api/auth/register"):
        config = REGISTER_RATE_LIMIT_CONFIG
    else:
        # Default API limit
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=10000,
            requests_per_day=100000
        )
    
    # Get client identifier (IP address or forwarded IP)
    client_id = get_client_identifier(request)
    
    # Check rate limit
    status = rate_limiter.check_limit(client_id, config)
    
    if not status.allowed:
        return Response(
            content={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Retry in {status.retry_after_seconds} seconds.",
            },
            status_code=429,
            headers={
                "Retry-After": str(status.retry_after_seconds),
                **status.to_headers(),
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    for header, value in status.to_headers().items():
        response.headers[header] = value
    
    return response
```

## Client Library Examples

### Python Client

```python
import requests
import time
from app.rate_limiter import RateLimitConfig, RateLimiter
from datetime import datetime

class RateLimitedClient:
    def __init__(self, base_url, strategy="sliding_window"):
        self.base_url = base_url
        self.limiter = RateLimiter(strategy=strategy)
        self.client_id = "python_client_1"
        self.config = RateLimitConfig(requests_per_minute=50)
    
    def request(self, method, endpoint, **kwargs):
        """Make request with built-in rate limiting"""
        # Check limit before making request
        status = self.limiter.check_limit(self.client_id, self.config, datetime.utcnow())
        
        if not status.allowed:
            # Wait and retry
            wait_time = status.retry_after_seconds
            print(f"Rate limit hit. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            return self.request(method, endpoint, **kwargs)
        
        # Make request
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 429:
            # Handle rate limit error
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retry after {retry_after}s")
            time.sleep(retry_after)
            return self.request(method, endpoint, **kwargs)
        
        return response
```

### JavaScript Client

```javascript
class RateLimitedFetch {
  constructor(baseURL, config = {}) {
    this.baseURL = baseURL;
    this.requestCount = 0;
    this.windowStart = Date.now();
    this.requestsPerMinute = config.requestsPerMinute || 100;
  }

  async request(endpoint, options = {}) {
    const now = Date.now();
    const windowAge = now - this.windowStart;

    // Reset window if minute has passed
    if (windowAge > 60000) {
      this.requestCount = 0;
      this.windowStart = now;
    }

    // Check rate limit
    if (this.requestCount >= this.requestsPerMinute) {
      const waitTime = 60000 - windowAge;
      console.log(`Rate limit. Waiting ${waitTime}ms...`);
      await new Promise(r => setTimeout(r, waitTime));
      return this.request(endpoint, options);
    }

    this.requestCount++;

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        'Content-Type': 'application/json',
      }
    });

    // Handle 429 responses
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || 60;
      console.log(`Rate limited. Retry after ${retryAfter}s`);
      await new Promise(r => setTimeout(r, retryAfter * 1000));
      return this.request(endpoint, options);
    }

    return response;
  }
}
```

## Rate Limiting Strategies Comparison

| Aspect | Fixed Window | Sliding Window | Token Bucket |
|--------|--------------|----------------|--------------|
| **Accuracy** | Low | High | Medium |
| **Memory Usage** | O(1) | O(n) | O(1) |
| **CPU Usage** | O(1) | O(n) | O(1) |
| **Boundary Issues** | Severe | None | None |
| **Burst Support** | Poor | Good | Excellent |
| **Best For** | High volume | General purpose | Bursty traffic |

## Best Practices

### 1. Choose the Right Strategy

```python
# High-volume public API - accuracy less critical
limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)

# Standard API - good accuracy and fairness
limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)

# APIs with bursty traffic - allow controlled bursts
limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
```

### 2. Different Limits for Different Operations

```python
def get_rate_limit_config(operation: str) -> RateLimitConfig:
    """Get appropriate rate limit for operation"""
    
    if operation == "read_factories":
        return RateLimitConfig(requests_per_minute=1000)
    elif operation == "create_factory":
        return RateLimitConfig(requests_per_minute=10)
    elif operation == "delete_factory":
        return RateLimitConfig(requests_per_minute=5)
    elif operation == "export_data":
        return RateLimitConfig(requests_per_minute=2)
    else:
        return RateLimitConfig(requests_per_minute=100)
```

### 3. Careful Burst Allowance Tuning

```python
# Reasonable burst for temporary spikes
RateLimitConfig(
    requests_per_minute=100,
    burst_allowance=1.5  # Good - allows 150 req spike
)

# No burst for strict limits
RateLimitConfig(
    requests_per_minute=10,
    burst_allowance=1.0  # Strict - no bursting
)
```

## Compliance and Security

### OWASP - A4:2021 – Insecure Direct Object References

Rate limiting helps prevent:
- Enumeration attacks on resource IDs
- Brute force attacks on APIs
- Unauthorized access attempts through trial-and-error

### NIST 800-63B - Authentication and Lifecycle Management

Supports:
- Rate limiting on authentication endpoints
- Protection against password spray attacks
- Brute force attack prevention

### PCI DSS - Requirement 6.5.10

Compliance requirement for:
- Broken authentication prevention
- Session management security
- Account lockout mechanisms

### GDPR - Article 32 (Security of Processing)

Rate limiting as part of:
- Technical and organizational measures
- Protection against unauthorized use
- Security risk mitigation

### SOC 2 Type II - CC6 Logical Access

Controls for:
- Prevention of unauthorized access attempts
- Detection of abuse patterns
- Fair resource allocation

## Testing

### Unit Testing Rate Limiting

```python
from datetime import datetime, timedelta
from app.rate_limiter import (
    RateLimiter,
    RateLimitStrategy,
    RateLimitConfig
)

def test_rate_limit():
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(requests_per_minute=3)
    now = datetime(2024, 1, 15, 10, 30, 0)
    
    # First 3 requests allowed
    for i in range(3):
        status = limiter.check_limit("user", config, now)
        assert status.allowed is True
    
    # 4th request denied
    status = limiter.check_limit("user", config, now)
    assert status.allowed is False
    assert status.retry_after_seconds > 0
    
    # After reset, allowed again
    later = now + timedelta(minutes=1)
    status = limiter.check_limit("user", config, later)
    assert status.allowed is True
```

## Summary

Rate limiting is essential for:
- **Security**: Preventing brute force and enumeration attacks
- **Fairness**: Ensuring all users get reasonable access
- **Stability**: Preventing resource exhaustion from traffic spikes
- **Compliance**: Meeting regulatory requirements for access control

Choose sliding window for most applications, fixed window for high-volume APIs, and token bucket for bursty workloads. Monitor rate limit events and adjust limits based on usage patterns.
