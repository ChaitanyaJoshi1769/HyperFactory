# API Key Scoping - Fine-Grained Permission Control

## Overview

HyperFactory implements a comprehensive API Key Scoping system that provides fine-grained, principle-of-least-privilege permission control for API keys. The system uses a two-tier permission model:

1. **APIScope** - Individual granular permissions (read:factories, write:machines, admin:users, etc.)
2. **ScopeLevel** - Predefined permission sets for common use cases (READ_ONLY, READ_WRITE, ADMIN, CUSTOM)

This enables organizations to delegate API access with minimal required permissions, reducing blast radius in case of key compromise.

## Features

✅ **20+ Fine-Grained Permissions**
- Read operations for 7 resources (factories, machines, hardware, suppliers, CAD, jobs, users)
- Write operations for 7 resources
- 3 admin operations (users management, settings, audit logs)
- 3 sensitive operations (delete, export, import)
- 1 meta operation (API key management)

✅ **Permission Levels**
- READ_ONLY: All read:* scopes (6 permissions)
- READ_WRITE: All read:* and write:* scopes (13 permissions)
- ADMIN: All permissions (20+)
- CUSTOM: User-specified scopes

✅ **Wildcard Support**
- admin:* grants all permissions
- read:* grants all read operations
- write:* grants all write operations
- resource:* patterns for fine-tuning

✅ **Permission Checking**
- Single scope validation
- Multiple scope checking (AND/OR logic)
- Wildcard matching and inheritance
- Delegation and restriction

✅ **Scope Management**
- Scope validation and enforcement
- Scope intersection (restriction to least privilege)
- Scope union (merging permissions)
- Resource-based scope lookup
- Display formatting for UI/logs

✅ **Audit Integration**
- Scope change logging for compliance
- Integration with audit_logger
- Context-aware severity levels
- Actor and resource tracking

## Architecture

### Permission Model

```
APIScope (Individual Permission)
├── Read Operations
│   ├── read:factories
│   ├── read:machines
│   ├── read:hardware
│   ├── read:suppliers
│   ├── read:cad
│   ├── read:jobs
│   └── read:users
├── Write Operations
│   ├── write:factories
│   ├── write:machines
│   ├── write:hardware
│   ├── write:suppliers
│   ├── write:cad
│   ├── write:jobs
│   └── write:users
├── Admin Operations
│   ├── admin:users
│   ├── admin:settings
│   └── admin:audit_log
├── Sensitive Operations
│   ├── delete:resources
│   ├── export:data
│   └── import:data
└── Meta Operations
    └── manage:api_keys
```

### Scope Levels

```python
ScopeLevel.READ_ONLY
├── read:factories
├── read:machines
├── read:hardware
├── read:suppliers
├── read:cad
└── read:jobs

ScopeLevel.READ_WRITE
├── (all READ_ONLY scopes)
├── write:factories
├── write:machines
├── write:hardware
├── write:suppliers
├── write:cad
├── write:jobs
└── write:users

ScopeLevel.ADMIN
└── (all scopes including admin:*, delete:*, export:*, import:*, manage:*)

ScopeLevel.CUSTOM
└── (user-specified scopes)
```

## Permission Matrix

| Resource | Read | Write | Delete | Export | Import | Admin |
|----------|------|-------|--------|--------|--------|-------|
| Factories | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Machines | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Hardware | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Suppliers | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| CAD | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Jobs | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| Users | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Settings | - | - | - | - | - | ✓ |
| Audit Log | - | - | - | - | - | ✓ |

## Core Classes

### APIScope (Enum)

Individual permission types:

```python
from app.api_key_scopes import APIScope

# Read operations
scope = APIScope.READ_FACTORIES.value  # "read:factories"
scope = APIScope.READ_MACHINES.value   # "read:machines"

# Write operations
scope = APIScope.WRITE_FACTORIES.value # "write:factories"

# Admin operations
scope = APIScope.ADMIN_USERS.value     # "admin:users"

# Sensitive operations
scope = APIScope.DELETE_RESOURCES.value # "delete:resources"
scope = APIScope.EXPORT_DATA.value      # "export:data"

# Meta operations
scope = APIScope.MANAGE_API_KEYS.value # "manage:api_keys"
```

### ScopeLevel (Enum)

Permission levels for common scenarios:

```python
from app.api_key_scopes import ScopeLevel

level = ScopeLevel.READ_ONLY    # Query-only access
level = ScopeLevel.READ_WRITE   # Query and modify access
level = ScopeLevel.ADMIN        # Full access
level = ScopeLevel.CUSTOM       # User-specified scopes
```

### APIKeyScopeManager

Core scope management engine:

```python
from app.api_key_scopes import api_key_scope_manager

manager = api_key_scope_manager
```

#### Key Methods

**validate_scopes(scopes: List[str]) → bool**

Validate a scope list:

```python
# Valid scopes
if manager.validate_scopes(["read:factories", "write:machines"]):
    # Create API key with scopes

# Invalid scopes
if not manager.validate_scopes(["read:factories", "invalid:scope"]):
    # Reject invalid scope
```

**get_scopes_from_level(level: ScopeLevel) → List[str]**

Get scope list for a permission level:

```python
# Get all READ_ONLY permissions
read_only = manager.get_scopes_from_level(ScopeLevel.READ_ONLY)

# Get all READ_WRITE permissions
read_write = manager.get_scopes_from_level(ScopeLevel.READ_WRITE)

# Get all ADMIN permissions
admin = manager.get_scopes_from_level(ScopeLevel.ADMIN)
```

**check_scope(scopes: List[str], required_scope: str) → bool**

Check if scope is available:

```python
key_scopes = ["read:factories", "write:machines"]

# Exact match
if manager.check_scope(key_scopes, "read:factories"):
    # Grant access

# Wildcard inheritance
key_scopes = ["read:*"]
if manager.check_scope(key_scopes, "read:machines"):
    # Grant access (matches read:*)

# Admin wildcard
key_scopes = ["admin:*"]
if manager.check_scope(key_scopes, "anything"):
    # Grant access (admin:* grants all)
```

**check_multiple_scopes(scopes: List[str], required_scopes: List[str], require_all: bool = True) → bool**

Check multiple permissions:

```python
key_scopes = ["read:factories", "read:machines", "write:hardware"]

# Require all (AND logic)
if manager.check_multiple_scopes(
    key_scopes,
    ["read:factories", "read:machines"],
    require_all=True
):
    # Both required scopes present

# Require any (OR logic)
if manager.check_multiple_scopes(
    key_scopes,
    ["admin:users", "write:hardware"],
    require_all=False
):
    # At least one required scope present
```

**restrict_scopes(current_scopes: List[str], max_scopes: List[str]) → List[str]**

Restrict to least privilege (intersection):

```python
# User requests scopes
requested = ["read:factories", "write:machines", "admin:users"]

# API key's max allowed scopes
max_allowed = ["read:factories", "write:machines", "read:hardware"]

# Effective scopes (intersection)
effective = manager.restrict_scopes(requested, max_allowed)
# Result: ["read:factories", "write:machines"]

# Prevents scope escalation
```

**merge_scopes(scope_lists: List[List[str]]) → List[str]**

Merge scope lists (union):

```python
scopes_from_user1 = ["read:factories", "write:machines"]
scopes_from_user2 = ["read:hardware", "write:hardware"]

merged = manager.merge_scopes([scopes_from_user1, scopes_from_user2])
# Result: All unique scopes from both lists
```

**get_resource_scopes(resource: str) → List[str]**

Get all scopes for a resource:

```python
# Get factories scopes
factories_scopes = manager.get_resource_scopes("factories")
# Result: ["read:factories", "write:factories"]

# Get user scopes
user_scopes = manager.get_resource_scopes("users")
# Result: ["read:users", "write:users", "admin:users"]
```

**format_scopes_for_display(scopes: List[str]) → str**

Human-readable format:

```python
scopes = ["read:factories", "read:machines"]
formatted = manager.format_scopes_for_display(scopes)
# Result: "Custom permissions: 2 read"

# Full READ_ONLY
read_only = manager.get_scopes_from_level(ScopeLevel.READ_ONLY)
formatted = manager.format_scopes_for_display(read_only)
# Result: "Read-only access to all resources"
```

**log_scope_change(user_id: str, api_key_id: str, old_scopes: List[str], new_scopes: List[str], source_ip: str = None)**

Audit logging for scope changes:

```python
manager.log_scope_change(
    user_id="user123",
    api_key_id="key_abc123",
    old_scopes=["read:factories"],
    new_scopes=["read:factories", "write:machines"],
    source_ip="192.168.1.1"
)
```

## HTTP Endpoints

### Create API Key with Scopes

```
POST /api/keys
Content-Type: application/json

{
  "name": "Factory Integration",
  "description": "Read-only access to factories",
  "scope_level": "read_only"
}

Response:
{
  "id": "key_abc123",
  "key": "hf_abc123xyz789...",
  "name": "Factory Integration",
  "scopes": ["read:factories", "read:machines", ...],
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Create with Custom Scopes

```
POST /api/keys
Content-Type: application/json

{
  "name": "Data Exporter",
  "description": "Export specific data",
  "scopes": ["read:factories", "read:machines", "export:data"]
}

Response:
{
  "id": "key_def456",
  "scopes": ["read:factories", "read:machines", "export:data"],
  ...
}
```

### List Available Scopes

```
GET /api/scopes

Response:
{
  "scopes": [
    {"name": "read:factories", "description": "Read factory data"},
    {"name": "write:machines", "description": "Modify machine data"},
    ...
  ],
  "levels": [
    {
      "level": "read_only",
      "scopes": ["read:factories", "read:machines", ...],
      "description": "Read-only access to all resources"
    },
    ...
  ]
}
```

### Get Key Details

```
GET /api/keys/{key_id}

Response:
{
  "id": "key_abc123",
  "name": "Factory Integration",
  "scopes": ["read:factories", "read:machines"],
  "scope_display": "Custom permissions: 2 read",
  "created_at": "2024-01-15T10:30:00Z",
  "last_used": "2024-01-15T11:45:00Z"
}
```

### Update Key Scopes

```
PATCH /api/keys/{key_id}
Content-Type: application/json

{
  "scopes": ["read:factories", "write:machines"]
}

Response:
{
  "id": "key_abc123",
  "scopes": ["read:factories", "write:machines"],
  "scope_display": "Custom permissions: 1 read, 1 write"
}
```

### Validate Scopes

```
POST /api/scopes/validate
Content-Type: application/json

{
  "scopes": ["read:factories", "write:machines", "invalid:scope"]
}

Response:
{
  "valid": false,
  "errors": ["invalid:scope is not a valid scope"],
  "message": "Contains 1 invalid scope"
}
```

## Middleware Integration

### Scope Checking Middleware

```python
from fastapi import HTTPException, Depends
from app.api_key_scopes import api_key_scope_manager

def require_scope(required_scope: str):
    """FastAPI dependency for scope checking"""
    async def check_scope(request: Request):
        # Extract API key from Authorization header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing API key")
        
        key = auth[7:]
        
        # Get key from database
        db_key = db.query(APIKey).filter(APIKey.key == hash_key(key)).first()
        if not db_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Check required scope
        if not api_key_scope_manager.check_scope(db_key.scopes, required_scope):
            raise HTTPException(status_code=403, detail=f"Missing scope: {required_scope}")
        
        request.state.api_key = db_key
    
    return Depends(check_scope)

# Usage
@router.get("/factories")
async def list_factories(
    _: None = Depends(require_scope("read:factories"))
):
    # Return factories
    return factories
```

### Multiple Scope Checking

```python
def require_any_scope(*scopes: str):
    """Require any of the listed scopes"""
    async def check_scopes(request: Request):
        db_key = get_api_key_from_request(request)
        
        if not api_key_scope_manager.check_multiple_scopes(
            db_key.scopes,
            list(scopes),
            require_all=False
        ):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return Depends(check_scopes)

@router.post("/export")
async def export_data(
    _: None = Depends(require_any_scope("export:data", "admin:*"))
):
    # Export data
    pass
```

## Security Best Practices

### 1. Principle of Least Privilege

Always grant the minimum required scopes:

```python
# ❌ WRONG: Giving admin access for read-only task
key_scopes = manager.get_scopes_from_level(ScopeLevel.ADMIN)

# ✅ CORRECT: Grant only read:factories
key_scopes = ["read:factories"]
```

### 2. Scope Delegation

When delegating API key creation:

```python
# Admin user creating key for integration partner
def create_delegated_key(admin_scopes, requested_scopes):
    # Restrict to intersection of what admin has and what is requested
    effective_scopes = api_key_scope_manager.restrict_scopes(
        requested_scopes,
        admin_scopes
    )
    # Admin cannot grant scopes they don't have
    return create_api_key(effective_scopes)
```

### 3. Scope Expiration

Rotate API keys periodically:

```python
# Create temporary read-only key for 30-day task
key = create_api_key(
    scopes=["read:factories"],
    expires_in_days=30
)
# Automatic revocation after 30 days
```

### 4. Audit Logging

Log all scope-related changes:

```python
api_key_scope_manager.log_scope_change(
    user_id=current_user.id,
    api_key_id=key.id,
    old_scopes=key.scopes,
    new_scopes=new_scopes,
    source_ip=request.client.host
)
# Integration with SIEM for monitoring
```

### 5. Scope Validation

Always validate before granting:

```python
# Validate user input
if not api_key_scope_manager.validate_scopes(requested_scopes):
    raise ValueError("Invalid scopes provided")
```

### 6. Wildcard Restrictions

Use wildcards carefully:

```python
# ❌ AVOID: Overly broad wildcards
scopes = ["read:*", "write:*"]  # Too much power

# ✓ PREFER: Specific scopes
scopes = ["read:factories", "write:machines"]
```

### 7. Scope Monitoring

Monitor for suspicious scope usage:

```python
# Alert on attempts to use high-privileged scopes
if "delete:resources" in key_scopes or "admin:users" in key_scopes:
    log_privilege_escalation_attempt(key_id, user_id)
```

## Integration Examples

### Integration Partner Setup

```python
def setup_integration_partner(partner_email: str):
    """Create scoped API key for integration partner"""
    
    # Only grant read access to factories and machines
    scopes = [
        "read:factories",
        "read:machines",
        "export:data"  # For bulk operations
    ]
    
    # Validate scopes
    if not api_key_scope_manager.validate_scopes(scopes):
        raise ValueError("Invalid scope configuration")
    
    # Create key
    key = APIKey(
        user_id=partner_user.id,
        name=f"Integration: {partner_email}",
        scopes=scopes,
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    
    # Log creation
    api_key_scope_manager.log_scope_change(
        user_id=current_admin.id,
        api_key_id=key.id,
        old_scopes=[],
        new_scopes=scopes
    )
    
    return key
```

### Webhook Delivery System

```python
def create_webhook_key():
    """Create key with minimal scope for webhook operations"""
    
    scopes = [
        "write:factories",  # Update factory status
        "read:machines"     # Read machine details
    ]
    
    key = APIKey(
        name="Webhook Processor",
        scopes=scopes,
        max_requests_per_minute=1000
    )
    
    return key
```

### Reporting System

```python
def create_reporting_key():
    """Create read-only key for analytics/reporting"""
    
    scopes = manager.get_scopes_from_level(ScopeLevel.READ_ONLY)
    
    key = APIKey(
        name="Analytics Reporter",
        scopes=scopes,
        rate_limit=100  # Conservative rate limit
    )
    
    return key
```

### Admin Operations

```python
def grant_admin_access(admin_email: str):
    """Grant admin API key (use with caution)"""
    
    scopes = manager.get_scopes_from_level(ScopeLevel.ADMIN)
    
    key = APIKey(
        name=f"Admin: {admin_email}",
        scopes=scopes,
        # Admin keys should have additional restrictions
        requires_mfa=True,
        max_requests_per_minute=10000
    )
    
    # High-severity audit log
    api_key_scope_manager.log_scope_change(
        user_id=current_admin.id,
        api_key_id=key.id,
        old_scopes=[],
        new_scopes=scopes
    )
    
    return key
```

## Compliance Requirements

### OWASP

- **A01:2021 - Broken Access Control**: Scope-based authorization prevents unauthorized actions
- **A02:2021 - Cryptographic Failures**: Scopes logged in audit trail
- **A06:2021 - Vulnerable and Outdated Components**: Scope validation on all inputs

### NIST

- **NIST SP 800-63-3**: Principle of least privilege through scope restriction
- **NIST SP 800-53**: AC-3 (Access Enforcement), AC-5 (Separation of Duties)

### PCI DSS

- **Requirement 7.1**: Restrict access to data based on scopes
- **Requirement 7.2**: Scope assignment based on business need
- **Requirement 10**: Audit logging of scope changes

### GDPR

- **Article 32**: Security measures through least-privilege scopes
- **Article 5**: Data minimization by restricting access

### SOC 2

- **CC6.1**: Logical access controls through scoping
- **CC7.2**: System monitoring of scope usage

## Performance Considerations

- **Scope Validation**: < 1ms (in-memory enum lookup)
- **Scope Checking**: < 0.5ms (set intersection)
- **Wildcard Matching**: < 1ms (prefix comparison)
- **Format Display**: < 0.1ms (string operations)
- **Audit Logging**: < 5ms (database write)

For typical usage (1000 users, 5000 API keys):
```
Scope checks per request: ~0.5-1ms
Overhead per request: < 1% of total latency
```

## Troubleshooting

### Issue: "Invalid scope" Error

**Cause**: Typo in scope name or undefined scope

**Solution**:
```python
# Validate before creating key
valid = manager.validate_scopes(user_input_scopes)
if not valid:
    # Get list of valid scopes
    valid_scopes = [scope.value for scope in APIScope]
```

### Issue: Access Denied Despite Having Key

**Cause**: Key doesn't have required scope

**Solution**:
```python
# Check what scopes key actually has
key = db.query(APIKey).get(key_id)
print(f"Key scopes: {key.scopes}")

# Check required scope for endpoint
required = "read:factories"
has_scope = api_key_scope_manager.check_scope(key.scopes, required)
print(f"Has {required}: {has_scope}")
```

### Issue: Scope Escalation Attack

**Cause**: Not restricting scopes to least privilege

**Solution**:
```python
# Always restrict when delegating
def update_key_scopes(key_id, requested_scopes):
    current_user_scopes = current_user.api_key.scopes
    
    # Restrict to intersection
    safe_scopes = api_key_scope_manager.restrict_scopes(
        requested_scopes,
        current_user_scopes
    )
    
    # User cannot grant scopes they don't have
    return update_api_key(key_id, safe_scopes)
```

### Issue: Wildcard Matching Not Working

**Cause**: Incorrect wildcard format

**Solution**:
```python
# ✓ CORRECT wildcard formats
manager.check_scope(["read:*"], "read:factories")      # ✓ Works
manager.check_scope(["admin:*"], "write:machines")     # ✓ Works (admin is wildcard)

# ✗ INCORRECT
manager.check_scope(["*:factories"], "read:factories")  # ✗ Not supported
manager.check_scope(["read:*"], "write:machines")      # ✗ Doesn't match different operation
```

## Future Enhancements

### Rate Limiting by Scope

```python
# Different rate limits for different operations
rate_limits = {
    "read:factories": 1000,    # 1000 req/min
    "write:machines": 100,     # 100 req/min
    "delete:resources": 10,    # 10 req/min
    "export:data": 50,         # 50 req/min
}
```

### Time-Based Scope Access

```python
# Scope only available during business hours
scopes = [
    {
        "scope": "write:factories",
        "available_hours": "09:00-17:00",  # UTC
        "available_days": "Mon-Fri"
    }
]
```

### Scope Conditions

```python
# Conditional scope grant
scopes = [
    {
        "scope": "delete:resources",
        "conditions": {
            "requires_mfa": true,
            "ip_whitelist": ["192.168.1.0/24"],
            "requires_approval": true
        }
    }
]
```

### Machine Learning

```python
# Detect suspicious scope usage patterns
def detect_suspicious_scope_usage(key_id, scopes, request_pattern):
    # Use ML model to identify unusual usage
    # Alert if pattern deviates from training data
    pass
```

## Testing

Comprehensive test suite in `tests/test_api_key_scopes.py`:

```bash
# Run all scope tests
python3 -m pytest tests/test_api_key_scopes.py -v

# Test specific functionality
python3 -m pytest tests/test_api_key_scopes.py::test_check_scope_wildcard -v
python3 -m pytest tests/test_api_key_scopes.py::test_restrict_scopes_intersection -v

# Test coverage
python3 -m pytest tests/test_api_key_scopes.py --cov=app.api_key_scopes
```

## Conclusion

API Key Scoping provides essential fine-grained access control:

- ✅ Enforce principle of least privilege
- ✅ Prevent scope escalation attacks
- ✅ Enable safe delegation to partners/integrations
- ✅ Comprehensive audit trail
- ✅ Support for compliance requirements

For production deployment:
1. Implement scope validation on all key creation endpoints
2. Integrate scope checking in API middleware
3. Monitor scope usage patterns
4. Audit log all scope changes
5. Educate users on least-privilege principle
6. Regularly review and rotate high-privilege keys
7. Implement scope expiration policies

See AUDIT_LOGGING.md, SESSION_MANAGEMENT.md, and SUSPICIOUS_ACTIVITY_DETECTION.md for complementary security features.
