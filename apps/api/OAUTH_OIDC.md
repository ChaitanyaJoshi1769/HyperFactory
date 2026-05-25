# OAuth 2.0 and OpenID Connect Provider - Identity Federation and Third-Party Authentication

## Overview

HyperFactory implements a complete OAuth 2.0 and OpenID Connect (OIDC) provider, enabling third-party authentication, identity federation, and delegated authorization. This implementation supports both web applications and mobile clients with industry-standard security practices including PKCE (Proof Key for Public Clients) and JWT-based identity tokens.

### Key Features

- **OAuth 2.0 Authorization Code Flow**: Industry-standard delegation flow
- **OpenID Connect (OIDC)**: Identity layer on top of OAuth 2.0
- **PKCE Support**: Secure authorization code flow for mobile and SPA clients
- **JWT ID Tokens**: Signed identity tokens for user information
- **Refresh Token Flow**: Long-lived access refresh without re-authentication
- **Fine-Grained Scopes**: Granular permission control (openid, profile, email, custom)
- **Confidential & Public Clients**: Support for both server and client-side applications
- **State & Nonce Parameters**: CSRF and replay attack prevention
- **Security Audit Logging**: Complete request tracing for compliance

## Architecture

### OAuth 2.0 vs OpenID Connect

**OAuth 2.0**: Authorization protocol
- Answers: "What can this app do?"
- Focused on delegated access to resources
- Returns: Access tokens for API calls

**OpenID Connect**: Identity layer on OAuth 2.0
- Answers: "Who is this user?"
- Extends OAuth 2.0 with identity verification
- Returns: ID tokens (JWTs) with user information

### Supported Flows

#### 1. Authorization Code Flow (Recommended for Web Apps)

**Most secure flow for web applications**

```
User → Browser → Authorization Server
                      ↓
                  User logs in
                  Grants permission
                  Redirects to app
                      ↓
App Backend → Authorization Server (exchange code for tokens)
                      ↓
            Returns access_token, id_token, refresh_token
```

**Characteristics:**
- Server-to-server token exchange (tokens never exposed to browser)
- CSRF protection via state parameter
- Supports refresh tokens
- Best for web applications

#### 2. Authorization Code Flow with PKCE (Recommended for Mobile/SPA)

**Secure flow for public clients (mobile apps, SPAs)**

```
Client → Authorization Server
             ↓
         User logs in
         Grants permission
         Redirects to app with code
             ↓
Client exchanges code + code_verifier for tokens
(No client secret needed)
```

**PKCE Protection:**
```
1. Client generates code_verifier (43-128 chars)
2. Client computes code_challenge = BASE64URL(SHA256(code_verifier))
3. Client sends challenge in auth request
4. Server stores challenge with authorization code
5. Client exchanges code + verifier
6. Server validates: BASE64URL(SHA256(verifier)) == stored challenge
```

**Prevents authorization code interception attacks**

## Configuration and API

### OAuth Client Registration

```python
from app.oauth_provider import (
    OAuthClient,
    OAuthGrantType,
    OAuthResponseType,
    OAuthScope,
    oauth_provider,
)

# Create OAuth client
client = OAuthClient(
    client_id="web_app_1",
    client_secret="super_secret_key_123",
    client_name="My Web App",
    redirect_uris=[
        "https://myapp.com/callback",
        "https://myapp.com/logout-callback",
    ],
    grant_types=[
        OAuthGrantType.AUTHORIZATION_CODE,
        OAuthGrantType.REFRESH_TOKEN,
    ],
    response_types=[OAuthResponseType.CODE],
    scopes=[
        OAuthScope.OPENID,
        OAuthScope.PROFILE,
        OAuthScope.EMAIL,
        OAuthScope.READ_FACTORIES,
    ],
    is_confidential=True,  # Server-side app
    is_trusted=False,  # Show consent screen
    requires_pkce=False,  # Not needed for server-side apps
)

# Register client
success, error = oauth_provider.register_client(client)
if success:
    print(f"Client registered: {client.client_id}")
```

### OAuth Scopes

| Scope | Purpose | Claims Returned |
|-------|---------|-----------------|
| `openid` | REQUIRED for OIDC | `sub` (user ID) |
| `profile` | User profile info | `name`, `family_name`, `given_name`, `picture`, `updated_at` |
| `email` | User email | `email`, `email_verified` |
| `read:profile` | Read user profile | User data |
| `write:profile` | Modify user profile | Ability to update |
| `read:factories` | Read factories | Factory list |
| `write:factories` | Modify factories | Create/update factories |

### Client Types

#### Confidential Client (Web Server)
- Can securely store client secret
- Uses client_secret in token requests
- Best for traditional web applications
- No PKCE required (but recommended for defense-in-depth)

```python
client = OAuthClient(
    client_id="web_backend",
    client_secret="very_secret_key",
    client_name="Web Backend",
    redirect_uris=["https://example.com/callback"],
    grant_types=[OAuthGrantType.AUTHORIZATION_CODE, OAuthGrantType.REFRESH_TOKEN],
    response_types=[OAuthResponseType.CODE],
    scopes=[OAuthScope.OPENID, OAuthScope.EMAIL],
    is_confidential=True,
    requires_pkce=False,  # Optional for confidential clients
)
```

#### Public Client (Mobile/SPA)
- Cannot securely store secrets
- Must use PKCE for authorization code flow
- Suitable for mobile apps and SPAs
- PKCE is required

```python
client = OAuthClient(
    client_id="mobile_app",
    client_secret="",  # No secret
    client_name="Mobile App",
    redirect_uris=["myapp://oauth-callback"],
    grant_types=[OAuthGrantType.AUTHORIZATION_CODE],
    response_types=[OAuthResponseType.CODE],
    scopes=[OAuthScope.OPENID, OAuthScope.PROFILE],
    is_confidential=False,
    requires_pkce=True,  # PKCE mandatory
)
```

## Authorization Code Flow Implementation

### Step 1: Authorization Request (Browser)

```
GET /oauth/authorize?
    client_id=web_app_1
    &response_type=code
    &redirect_uri=https://myapp.com/callback
    &scope=openid%20profile%20email
    &state=random_state_string
    &code_challenge=XxJlq2XVc7mJEtWuKWgHHas7Zs0cHexHXwJ8AG_8-2I
    &code_challenge_method=S256
```

**Parameters:**
- `client_id`: Registered client ID
- `response_type`: "code" for authorization code flow
- `redirect_uri`: Where to redirect after authorization
- `scope`: Space-separated requested scopes
- `state`: Random string to prevent CSRF (REQUIRED)
- `code_challenge`: PKCE code challenge (for public clients)
- `code_challenge_method`: "S256" for SHA256 (recommended)
- `nonce`: Random string for ID token validation (optional but recommended)

**Example in Python:**

```python
import secrets
import hashlib
import base64
from urllib.parse import urlencode

# Generate PKCE parameters
code_verifier = oauth_provider.generate_code_verifier()
code_challenge = oauth_provider.generate_code_challenge(code_verifier, "S256")
state = oauth_provider.generate_state()
nonce = oauth_provider.generate_nonce()

# Build authorization URL
auth_params = {
    "client_id": "mobile_app",
    "response_type": "code",
    "redirect_uri": "myapp://oauth-callback",
    "scope": "openid profile email",
    "state": state,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "nonce": nonce,
}

auth_url = f"https://api.hyperfactory.com/oauth/authorize?{urlencode(auth_params)}"

# User clicks link, logs in, grants permission
# Browser redirects to: myapp://oauth-callback?code=AUTHORIZATION_CODE&state=STATE_STRING
```

### Step 2: Authorization Code Creation

```python
code, error = oauth_provider.create_authorization_code(
    client_id="mobile_app",
    user_id="user_123",
    redirect_uri="myapp://oauth-callback",
    scope="openid profile email",
    code_challenge=code_challenge,
    code_challenge_method="S256",
)

if not error:
    print(f"Authorization code created: {code}")
    # Authorization code expires in 5 minutes
    # Single-use only (marked as used after token exchange)
```

### Step 3: Token Exchange (App Backend)

```python
# Receive authorization code from redirect
authorization_code = "AUTHORIZATION_CODE_FROM_REDIRECT"
state_from_redirect = "STATE_STRING_FROM_REDIRECT"

# Verify state matches (CSRF protection)
assert state_from_redirect == stored_state

# Exchange code for tokens
tokens, error = oauth_provider.exchange_authorization_code(
    code=authorization_code,
    client_id="mobile_app",
    redirect_uri="myapp://oauth-callback",
    code_verifier=code_verifier,  # Required for PKCE
)

if not error:
    access_token = tokens["access_token"]
    id_token = tokens["id_token"]
    refresh_token = tokens["refresh_token"]
    expires_in = tokens["expires_in"]  # 3600 seconds
    scope = tokens["scope"]
```

**Token Response:**

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGc...",
  "id_token": "eyJhbGc...",
  "scope": "openid profile email"
}
```

### Step 4: ID Token Verification

```python
# Verify and decode ID token
claims, error = oauth_provider.verify_id_token(
    id_token=id_token,
    client_id="mobile_app",
    nonce=nonce,  # Must match original nonce
)

if not error:
    # Extract user information
    user_id = claims["sub"]
    email = claims.get("email")
    name = claims.get("name")
    picture = claims.get("picture")
    
    # Claims include:
    # {
    #   "iss": "https://api.hyperfactory.com",
    #   "sub": "user_123",
    #   "aud": "mobile_app",
    #   "iat": 1749430500,
    #   "exp": 1749434100,
    #   "auth_time": 1749430500,
    #   "nonce": "original_nonce"
    # }
```

## Refresh Token Flow

### Using Refresh Token to Get New Access Token

```python
# When access token expires, use refresh token to get new one
tokens, error = oauth_provider.refresh_access_token(
    refresh_token=refresh_token,
    client_id="mobile_app",
)

if not error:
    new_access_token = tokens["access_token"]
    # Old refresh token might be rotated (implementation-dependent)
```

**When to Refresh:**
- Access token expires (check `expires_in` from token response)
- API returns 401 Unauthorized
- Before expiration (optional, for continuous operation)

## API Integration

### Using Access Token to Call APIs

```python
import requests

# Call protected API with access token
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
}

response = requests.get(
    "https://api.hyperfactory.com/api/factories",
    headers=headers,
)

if response.status_code == 200:
    factories = response.json()
elif response.status_code == 401:
    # Access token expired, use refresh token
    tokens = refresh_access_token(refresh_token, client_id)
    access_token = tokens["access_token"]
    # Retry request with new token
```

### Server-Side Validation

```python
# In protected endpoint middleware
def validate_oauth_token(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, "missing_token"
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, "invalid_auth_header"
    
    access_token = parts[1]
    
    # Validate token
    info, error = oauth_provider.validate_access_token(access_token)
    if error:
        return None, error
    
    # info contains: client_id, user_id, scope, expires_in
    return info, None
```

## FastAPI Middleware Integration

### Complete OAuth Middleware Example

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.middleware("http")
async def oauth_middleware(request: Request, call_next):
    """OAuth 2.0 middleware for protecting endpoints"""
    
    # Exempt public endpoints
    public_paths = {
        "/oauth/authorize",
        "/oauth/token",
        "/oauth/introspect",
        "/health",
        "/docs",
    }
    
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Validate OAuth token
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Missing authorization header"}
        )
    
    # Extract token
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_auth", "message": "Invalid authorization header"}
        )
    
    # Validate token
    info, error = oauth_provider.validate_access_token(token)
    if error:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_token", "message": error}
        )
    
    # Store token info in request for endpoint use
    request.state.oauth = info
    
    response = await call_next(request)
    return response
```

## Compliance and Security

### OWASP - A07:2021 – Identification and Authentication Failures

OAuth/OIDC implementation prevents:
- Password exposure (delegated authentication)
- Brute force attacks (auth server protection)
- Credential stuffing (no password database in client apps)
- Session fixation (unique tokens per session)

### NIST 800-63B - Authentication and Lifecycle Management

Supports:
- Memorized secret protection
- Single-factor OTP support
- Multi-factor authentication
- Credential management

### OpenID Connect Security Best Practices

- **State Parameter**: Prevent CSRF attacks
- **Nonce Parameter**: Prevent ID token replay attacks
- **PKCE**: Prevent authorization code interception
- **HTTPS Only**: Encrypt tokens in transit
- **Secure Token Storage**: Protect tokens from XSS

### Token Security

**Access Token:**
- Short-lived (1 hour default)
- No sensitive data in claims
- Validated on every API call
- Can be revoked

**ID Token:**
- Signed JWT with user claims
- Must validate signature
- Must verify audience (client_id)
- Must verify nonce (prevent replay)
- Expires after 1 hour

**Refresh Token:**
- Long-lived (30 days default)
- Can be revoked
- Should be stored securely
- Rotated on use (optional)

## Client Library Examples

### Python Client (Web App with Flask)

```python
from flask import Flask, redirect, request, session
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = "your_secret_key"

OAUTH_CONFIG = {
    "client_id": "web_app_1",
    "client_secret": "super_secret",
    "auth_url": "https://api.hyperfactory.com/oauth/authorize",
    "token_url": "https://api.hyperfactory.com/oauth/token",
    "redirect_uri": "https://myapp.com/oauth/callback",
    "scopes": ["openid", "profile", "email"],
}

@app.route("/login")
def login():
    """Redirect to OAuth authorization server"""
    params = {
        "client_id": OAUTH_CONFIG["client_id"],
        "response_type": "code",
        "redirect_uri": OAUTH_CONFIG["redirect_uri"],
        "scope": " ".join(OAUTH_CONFIG["scopes"]),
        "state": secrets.token_urlsafe(32),
    }
    
    session["oauth_state"] = params["state"]
    auth_url = f"{OAUTH_CONFIG['auth_url']}?{urlencode(params)}"
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth callback"""
    # Verify state
    state = request.args.get("state")
    if state != session.pop("oauth_state"):
        return "CSRF validation failed", 403
    
    # Get authorization code
    code = request.args.get("code")
    if not code:
        return "No authorization code", 400
    
    # Exchange code for tokens
    token_response = requests.post(
        OAUTH_CONFIG["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": OAUTH_CONFIG["client_id"],
            "client_secret": OAUTH_CONFIG["client_secret"],
            "redirect_uri": OAUTH_CONFIG["redirect_uri"],
        }
    )
    
    if token_response.status_code != 200:
        return "Token exchange failed", 400
    
    tokens = token_response.json()
    session["access_token"] = tokens["access_token"]
    session["refresh_token"] = tokens["refresh_token"]
    
    return redirect("/")
```

### JavaScript Client (React SPA with PKCE)

```javascript
import { useState, useEffect } from 'react';

const OAuth2Flow = () => {
  const clientId = 'spa_app_1';
  const authServerUrl = 'https://api.hyperfactory.com/oauth';
  const redirectUri = 'https://myapp.com/callback';
  const scope = 'openid profile email';

  const generatePKCE = async () => {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const verifier = btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');

    const hash = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(verifier)
    );
    const challenge = btoa(String.fromCharCode(...new Uint8Array(hash)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');

    return { verifier, challenge };
  };

  const handleLogin = async () => {
    const { verifier, challenge } = await generatePKCE();
    const state = btoa(Math.random().toString());
    const nonce = btoa(Math.random().toString());

    // Store verifier, state, nonce in sessionStorage
    sessionStorage.setItem('pkce_verifier', verifier);
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_nonce', nonce);

    // Redirect to authorization server
    const authUrl = new URL(`${authServerUrl}/authorize`);
    authUrl.searchParams.append('client_id', clientId);
    authUrl.searchParams.append('response_type', 'code');
    authUrl.searchParams.append('redirect_uri', redirectUri);
    authUrl.searchParams.append('scope', scope);
    authUrl.searchParams.append('state', state);
    authUrl.searchParams.append('code_challenge', challenge);
    authUrl.searchParams.append('code_challenge_method', 'S256');
    authUrl.searchParams.append('nonce', nonce);

    window.location.href = authUrl.toString();
  };

  return <button onClick={handleLogin}>Login with OAuth</button>;
};
```

## Testing

### Unit Testing OAuth Provider

```python
from app.oauth_provider import (
    OAuthProviderManager,
    OAuthClient,
    OAuthGrantType,
    OAuthResponseType,
    OAuthScope,
)

def test_authorization_code_flow():
    """Test complete authorization code flow"""
    manager = OAuthProviderManager()
    
    # Register client
    client = OAuthClient(
        client_id="test_app",
        client_secret="secret",
        client_name="Test",
        redirect_uris=["https://example.com/callback"],
        grant_types=[OAuthGrantType.AUTHORIZATION_CODE],
        response_types=[OAuthResponseType.CODE],
        scopes=[OAuthScope.OPENID],
    )
    manager.register_client(client)
    
    # Create authorization code
    code, _ = manager.create_authorization_code(
        client_id="test_app",
        user_id="user1",
        redirect_uri="https://example.com/callback",
        scope="openid",
    )
    assert code is not None
    
    # Exchange code for tokens
    tokens, _ = manager.exchange_authorization_code(
        code=code,
        client_id="test_app",
        redirect_uri="https://example.com/callback",
    )
    
    assert "access_token" in tokens
    assert "id_token" in tokens
    assert tokens["token_type"] == "Bearer"
```

## Troubleshooting

### Issue: "invalid_client"
- Verify client_id is registered
- Check client_secret matches (for confidential clients)
- Ensure client has been registered with `register_client()`

### Issue: "invalid_redirect_uri"
- Verify redirect_uri exactly matches registered URI
- Check for protocol (http vs https)
- Ensure no trailing slashes mismatch

### Issue: "invalid_scope"
- Verify scope is allowed for client
- Check scope names are correct (case-sensitive)
- Ensure scope is in space-separated format

### Issue: PKCE validation fails
- Verify code_verifier is the original one used to generate challenge
- Check code_challenge_method is "S256" (not "plain")
- Ensure no URL encoding issues

## Summary

OAuth 2.0 and OpenID Connect provide:
- **Secure Delegation**: Users don't share passwords with apps
- **Standards-Based**: Industry-standard protocols
- **Flexible**: Supports web, mobile, and SPA clients
- **Extensible**: Easy to add social login providers
- **Compliance**: Supports security and privacy regulations

Implement OAuth/OIDC for better security and user experience.
