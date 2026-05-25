# HyperFactory Authentication System - Phase 3

Comprehensive JWT and API Key authentication with role-based access control (RBAC).

## Overview

The authentication system provides:
- **JWT Token Authentication**: Bearer token-based session management with configurable expiration
- **API Key Authentication**: Programmatic access with secure key hashing and expiration support
- **User Management**: Registration, login, profile updates, and account deactivation
- **Role-Based Access Control**: Four-tier permission system (user, admin, engineer, manager)
- **Middleware & Decorators**: Flexible authentication dependencies for endpoint protection

## Architecture

### Security Layer (`app/security.py`)

Core cryptographic functions:

```python
# Password hashing
get_password_hash(password: str) -> str
verify_password(plain: str, hashed: str) -> bool

# JWT tokens
create_access_token(data: dict, expires_delta: Optional[timedelta]) -> str
verify_token(token: str) -> Optional[str]  # Returns subject (user_id)
decode_access_token(token: str) -> dict  # Returns full payload
```

**Configuration**:
- `JWT_SECRET_KEY`: Environment variable (default: "hyperfactory-dev-secret-key-change-in-production")
- `ALGORITHM`: "HS256" (HMAC SHA256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Environment variable (default: 1440 = 24 hours)

### Auth Service (`app/services/auth_service.py`)

Business logic for user and token management.

**User Management**:
```python
create_user(db, user: UserCreate) -> User
get_user(db, user_id: UUID) -> Optional[User]
get_user_by_username(db, username: str) -> Optional[User]
get_user_by_email(db, email: str) -> Optional[User]
authenticate_user(db, login: UserLogin) -> Optional[User]
update_user(db, user_id, full_name, organization, password) -> Optional[User]
deactivate_user(db, user_id) -> bool
activate_user(db, user_id) -> bool
```

**Token Management**:
```python
create_access_token_for_user(user: User, expires_delta) -> str
verify_user_token(token: str) -> Optional[UUID]
```

**API Key Management**:
```python
create_api_key(db, user_id, name, expires_at) -> (APIKey, key_value)
verify_api_key(db, key: str) -> Optional[UUID]
revoke_api_key(db, api_key_id) -> bool
list_user_api_keys(db, user_id) -> List[APIKey]
delete_api_key(db, api_key_id) -> bool
```

### Authentication Middleware (`app/middleware.py`)

Reusable dependencies for endpoint protection.

#### JWT Authentication

```python
get_current_user(credentials, db) -> User
```
Validates Bearer token and returns authenticated user.

```python
@router.get("/protected")
def protected_endpoint(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}"}
```

#### API Key Authentication

```python
get_current_user_from_api_key(x_api_key, db) -> User
```
Validates X-API-Key header and returns authenticated user.

```python
@router.get("/api-protected")
def api_protected_endpoint(user: User = Depends(get_current_user_from_api_key)):
    return {"message": f"Hello {user.username}"}
```

#### Dual Authentication (JWT or API Key)

```python
get_current_user_from_jwt_or_api_key(credentials, x_api_key, db) -> User
```
Accepts either Bearer token or X-API-Key header.

```python
@router.get("/dual-protected")
def dual_protected(user: User = Depends(get_current_user_from_jwt_or_api_key)):
    return {"message": f"Hello {user.username}"}
```

#### Role-Based Access Control

```python
require_role(role: str)
require_any_role(*roles: str)
require_permission(permission: str)
```

```python
@router.post("/admin-only")
def admin_endpoint(user: User = Depends(require_role("admin"))):
    return {"message": "Admin action"}

@router.post("/managers")
def manager_endpoint(user: User = Depends(require_any_role("admin", "manager"))):
    return {"message": "Manager action"}

@router.post("/manage-suppliers")
def manage_suppliers(user: User = Depends(require_permission("manage_suppliers"))):
    return {"message": "Supplier management"}
```

**Permission Map**:
- `manage_users`: admin only
- `manage_suppliers`: admin, manager
- `manage_factory`: admin, manager, engineer
- `manage_quotes`: admin, manager

### User Model (`app/models/user.py`)

**User Table**:
```
id              UUID (primary key)
username        VARCHAR(255) UNIQUE NOT NULL
email           VARCHAR(255) UNIQUE NOT NULL
full_name       VARCHAR(255)
hashed_password VARCHAR(255) NOT NULL
is_active       BOOLEAN DEFAULT true
is_admin        BOOLEAN DEFAULT false
role            VARCHAR(50) DEFAULT 'user'
organization    VARCHAR(255)
created_at      DATETIME DEFAULT now()
updated_at      DATETIME DEFAULT now()
last_login      DATETIME
```

**Roles**:
- `user`: Standard user with basic access
- `admin`: Full system access
- `engineer`: Technical operations and manufacturing
- `manager`: Business operations and reporting

**APIKey Table**:
```
id          UUID (primary key)
user_id     UUID (foreign key → users.id)
key_hash    VARCHAR(255) UNIQUE NOT NULL
name        VARCHAR(255) NOT NULL
is_active   BOOLEAN DEFAULT true
last_used   DATETIME
created_at  DATETIME DEFAULT now()
expires_at  DATETIME
```

## Endpoints

### User Registration & Login

#### POST `/api/auth/register`
Register a new user.

**Request**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "organization": "ACME Corp"
}
```

**Response** (201):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "organization": "ACME Corp",
  "is_active": true,
  "is_admin": false,
  "role": "user",
  "created_at": "2026-05-25T12:30:00",
  "updated_at": "2026-05-25T12:30:00"
}
```

**Error Cases**:
- 409 Conflict: Username or email already exists
- 422 Unprocessable Entity: Validation error (short password, invalid email)

#### POST `/api/auth/login`
Authenticate user and get access token.

**Request**:
```json
{
  "username": "john_doe",
  "password": "SecurePassword123!"
}
```

**Response** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Cases**:
- 401 Unauthorized: Invalid username/password or inactive account

### User Profile

#### GET `/api/auth/me`
Get current authenticated user.

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "organization": "ACME Corp",
  "is_active": true,
  "is_admin": false,
  "role": "user",
  "created_at": "2026-05-25T12:30:00",
  "updated_at": "2026-05-25T12:30:00"
}
```

#### PUT `/api/auth/me`
Update current user profile.

**Headers**: `Authorization: Bearer {access_token}`

**Request**:
```json
{
  "full_name": "John D. Doe",
  "organization": "ACME Corp, Inc.",
  "password": "NewSecurePassword123!"
}
```

**Response** (200): Updated user object

### API Key Management

#### POST `/api/auth/api-keys`
Create new API key for programmatic access.

**Headers**: `Authorization: Bearer {access_token}`

**Request**:
```json
{
  "name": "CI/CD Pipeline",
  "expires_at": "2027-05-25T00:00:00"
}
```

**Response** (201):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "CI/CD Pipeline",
  "key": "s7pM9kL2qW5xR8vN3tY6uJ9oI4aS1dF6gH7j",
  "created_at": "2026-05-25T12:30:00",
  "message": "Save this key securely. You won't be able to see it again."
}
```

**Important**: The key is only shown once. Store it securely in an environment variable or secrets manager.

#### GET `/api/auth/api-keys`
List all API keys for current user.

**Headers**: `Authorization: Bearer {access_token}`

**Response** (200):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "CI/CD Pipeline",
    "is_active": true,
    "created_at": "2026-05-25T12:30:00",
    "last_used": "2026-05-25T14:15:30",
    "expires_at": "2027-05-25T00:00:00"
  }
]
```

#### DELETE `/api/auth/api-keys/{key_id}`
Permanently delete an API key.

**Headers**: `Authorization: Bearer {access_token}`

**Response**: 204 No Content

#### POST `/api/auth/api-keys/{key_id}/revoke`
Revoke (deactivate) an API key without deleting it.

**Headers**: `Authorization: Bearer {access_token}`

**Response**: 204 No Content

## Usage Examples

### Client-Side: Register & Login

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

### Accessing Protected Endpoints

**With JWT Token**:
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**With API Key**:
```bash
curl http://localhost:8000/hardware/materials \
  -H "X-API-Key: s7pM9kL2qW5xR8vN3tY6uJ9oI4aS1dF6gH7j"
```

### Programmatic Usage (Python)

```python
import requests

# Register
response = requests.post(
    "http://localhost:8000/api/auth/register",
    json={
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePassword123!",
    }
)
user_id = response.json()["id"]

# Login
response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "john_doe", "password": "SecurePassword123!"}
)
token = response.json()["access_token"]

# Access protected endpoint
response = requests.get(
    "http://localhost:8000/api/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
```

## Security Best Practices

### For Developers

1. **Never hardcode secrets**: Use environment variables for JWT_SECRET_KEY
2. **Use HTTPS in production**: Always encrypt tokens in transit
3. **Validate input**: Pydantic schemas enforce minimum password length (8 chars)
4. **Hash passwords**: bcrypt automatically handles salt and iterations
5. **Protect API keys**: Treat API keys like passwords; never log or expose them
6. **Set expiration**: Configure appropriate token/key expiration times
7. **Rotate secrets**: Periodically regenerate JWT_SECRET_KEY and create new API keys
8. **Audit access**: Log authentication events and API key usage

### For Users

1. **Strong passwords**: Use 12+ characters with mixed case, numbers, and symbols
2. **Unique credentials**: Don't reuse passwords across services
3. **Secure storage**: Store API keys in secure vaults or environment variables
4. **Revoke compromised keys**: Immediately revoke any exposed API keys
5. **Regular rotation**: Create new API keys periodically
6. **Account recovery**: Enable multi-factor authentication when available

## Environment Variables

```bash
# Required
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters

# Optional (defaults shown)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=development
```

## Testing

Run authentication tests:

```bash
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::test_register_new_user -v

# With coverage
pytest tests/test_auth.py --cov=app.services.auth_service
```

## Migration

Database migrations for user tables:

```bash
# Apply migrations
alembic upgrade head

# View migration history
alembic current
alembic history

# Rollback (if needed)
alembic downgrade -1
```

## Future Enhancements

1. **Multi-Factor Authentication (MFA)**: TOTP/SMS verification
2. **OAuth2/OIDC**: Social login support (Google, GitHub, etc.)
3. **Refresh Tokens**: Implement token refresh mechanism
4. **Rate Limiting**: Login attempt throttling
5. **Account Lockout**: Automatic lockout after failed attempts
6. **Audit Logging**: Comprehensive security event tracking
7. **SSO Integration**: Enterprise single sign-on support
8. **SAML Support**: SAML 2.0 authentication for enterprise

## Troubleshooting

### "Invalid token"
- Ensure Bearer prefix in Authorization header: `Authorization: Bearer {token}`
- Check token hasn't expired
- Verify JWT_SECRET_KEY matches signing key

### "User not found"
- User may have been deactivated or deleted
- Check user exists: `GET /api/auth/me`

### "API key not found"
- Key may have been deleted or revoked
- Create new key: `POST /api/auth/api-keys`

### Password doesn't work
- Ensure correct case sensitivity
- Reset password via `PUT /api/auth/me`

## See Also

- [API Documentation](./API.md) - Full endpoint reference
- [Migrations Guide](./MIGRATIONS.md) - Database management
- [Phase 2 Completion](./PHASE-2-COMPLETION.md) - Backend overview
