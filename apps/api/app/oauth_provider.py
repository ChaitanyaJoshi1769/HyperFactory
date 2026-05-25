"""OAuth 2.0 and OpenID Connect Provider - Third-party authentication and identity federation"""

import secrets
import hashlib
import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from enum import Enum
import jwt

# Configuration
OAUTH_PROVIDER_NAME = "HyperFactory"
OAUTH_AUTHORIZATION_CODE_TTL_SECONDS = 300  # 5 minutes
OAUTH_ACCESS_TOKEN_TTL_SECONDS = 3600  # 1 hour
OAUTH_REFRESH_TOKEN_TTL_SECONDS = 2592000  # 30 days
OAUTH_ID_TOKEN_TTL_SECONDS = 3600  # 1 hour
PKCE_CODE_CHALLENGE_METHOD = "S256"  # SHA256


class OAuthGrantType(str, Enum):
    """OAuth 2.0 Grant Types"""
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"  # Resource Owner Password Credentials (not recommended)


class OAuthResponseType(str, Enum):
    """OAuth 2.0 Response Types"""
    CODE = "code"  # Authorization Code Flow
    TOKEN = "token"  # Implicit Flow (deprecated, not recommended)
    ID_TOKEN = "id_token"  # Implicit Flow with OIDC
    CODE_ID_TOKEN = "code id_token"  # Hybrid Flow


class OAuthScope(str, Enum):
    """OAuth 2.0 and OIDC Scopes"""
    # OpenID Connect scopes
    OPENID = "openid"  # Required for OIDC
    PROFILE = "profile"  # Name, family_name, given_name, picture, updated_at
    EMAIL = "email"  # Email and email_verified

    # Custom scopes
    READ_PROFILE = "read:profile"  # Read user profile
    WRITE_PROFILE = "write:profile"  # Modify user profile
    READ_FACTORIES = "read:factories"  # Read factories
    WRITE_FACTORIES = "write:factories"  # Modify factories


class PKCEMethod(str, Enum):
    """PKCE Code Challenge Methods"""
    PLAIN = "plain"  # No hashing (not recommended)
    S256 = "S256"  # SHA256 hashing (recommended)


class OAuthClient:
    """OAuth 2.0 Client Configuration"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        client_name: str,
        redirect_uris: List[str],
        grant_types: List[OAuthGrantType],
        response_types: List[OAuthResponseType],
        scopes: List[OAuthScope],
        is_confidential: bool = True,
        is_trusted: bool = False,
        requires_pkce: bool = True,
    ):
        """
        Initialize OAuth client.

        Args:
            client_id: Unique client identifier
            client_secret: Client secret (for confidential clients)
            client_name: Human-readable client name
            redirect_uris: Allowed redirect URIs for authorization code flow
            grant_types: Allowed grant types for this client
            response_types: Allowed response types
            scopes: Scopes this client can request
            is_confidential: Whether client can authenticate with secret
            is_trusted: Whether client skips consent screen
            requires_pkce: Whether PKCE is required (recommended for public clients)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_name = client_name
        self.redirect_uris = redirect_uris
        self.grant_types = grant_types
        self.response_types = response_types
        self.scopes = scopes
        self.is_confidential = is_confidential
        self.is_trusted = is_trusted
        self.requires_pkce = requires_pkce
        self.created_at = datetime.utcnow()
        self.last_used_at: Optional[datetime] = None

    def validate_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate that redirect_uri is registered for this client"""
        return redirect_uri in self.redirect_uris

    def validate_grant_type(self, grant_type: OAuthGrantType) -> bool:
        """Validate that grant type is allowed for this client"""
        return grant_type in self.grant_types

    def validate_response_type(self, response_type: OAuthResponseType) -> bool:
        """Validate that response type is allowed for this client"""
        return response_type in self.response_types

    def validate_scope(self, scope: str) -> bool:
        """Validate that requested scope is allowed for this client"""
        requested_scopes = scope.split()
        allowed_scope_values = [s.value for s in self.scopes]
        return all(s in allowed_scope_values for s in requested_scopes)


class AuthorizationCode:
    """OAuth 2.0 Authorization Code"""

    def __init__(
        self,
        code: str,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = PKCE_CODE_CHALLENGE_METHOD,
    ):
        """
        Initialize authorization code.

        Args:
            code: Authorization code value
            client_id: Client ID that requested the code
            user_id: User ID granting authorization
            redirect_uri: Redirect URI provided in authorization request
            scope: Granted scopes
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method (plain or S256)
        """
        self.code = code
        self.client_id = client_id
        self.user_id = user_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.code_challenge = code_challenge
        self.code_challenge_method = code_challenge_method
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=OAUTH_AUTHORIZATION_CODE_TTL_SECONDS)
        self.is_used = False

    def is_expired(self) -> bool:
        """Check if authorization code has expired"""
        return datetime.utcnow() > self.expires_at

    def validate_pkce(self, code_verifier: str) -> bool:
        """Validate PKCE code verifier"""
        if not self.code_challenge:
            return True  # PKCE not used

        if self.code_challenge_method == "plain":
            return code_verifier == self.code_challenge
        elif self.code_challenge_method == "S256":
            # Hash the verifier and compare
            hash_bytes = hashlib.sha256(code_verifier.encode()).digest()
            computed_challenge = base64.urlsafe_b64encode(hash_bytes).decode('utf-8').rstrip('=')
            return computed_challenge == self.code_challenge

        return False


class OAuthToken:
    """OAuth 2.0 Token (Access Token or ID Token)"""

    def __init__(
        self,
        token_type: str,  # "access", "id", "refresh"
        token_value: str,
        client_id: str,
        user_id: str,
        scope: str,
        issued_at: datetime,
        expires_in_seconds: int,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize OAuth token.

        Args:
            token_type: Type of token (access, id, refresh)
            token_value: Token value
            client_id: Client ID that received the token
            user_id: User ID for whom token was issued
            scope: Granted scopes
            issued_at: When token was issued
            expires_in_seconds: Token lifetime in seconds
            refresh_token: Associated refresh token (for access tokens)
        """
        self.token_type = token_type
        self.token_value = token_value
        self.client_id = client_id
        self.user_id = user_id
        self.scope = scope
        self.issued_at = issued_at
        self.expires_at = issued_at + timedelta(seconds=expires_in_seconds)
        self.expires_in = expires_in_seconds
        self.refresh_token = refresh_token

    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() > self.expires_at

    def get_remaining_lifetime(self) -> int:
        """Get remaining lifetime in seconds"""
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))


class OAuthProviderManager:
    """Manages OAuth 2.0 and OpenID Connect provider operations"""

    def __init__(self, signing_secret: str = ""):
        """
        Initialize OAuth provider.

        Args:
            signing_secret: Secret key for signing tokens (JWT)
        """
        self.signing_secret = signing_secret or secrets.token_hex(32)
        self.logger = logging.getLogger("oauth_provider")

        # In-memory storage (use database in production)
        self._clients: Dict[str, OAuthClient] = {}
        self._authorization_codes: Dict[str, AuthorizationCode] = {}
        self._tokens: Dict[str, OAuthToken] = {}

    @staticmethod
    def generate_client_id() -> str:
        """Generate random client ID"""
        return secrets.token_hex(16)

    @staticmethod
    def generate_client_secret() -> str:
        """Generate random client secret"""
        return secrets.token_hex(32)

    @staticmethod
    def generate_authorization_code() -> str:
        """Generate random authorization code"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_access_token() -> str:
        """Generate random access token"""
        return secrets.token_urlsafe(48)

    @staticmethod
    def generate_refresh_token() -> str:
        """Generate random refresh token"""
        return secrets.token_urlsafe(48)

    @staticmethod
    def generate_state() -> str:
        """Generate random state parameter for CSRF protection"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_nonce() -> str:
        """Generate random nonce for replay attack prevention"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate PKCE code verifier (43-128 characters)"""
        # RFC 7636: code_verifier = 43*128unreserved
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_code_challenge(code_verifier: str, method: str = PKCE_CODE_CHALLENGE_METHOD) -> str:
        """
        Generate PKCE code challenge from verifier.

        Args:
            code_verifier: PKCE code verifier
            method: Code challenge method (plain or S256)

        Returns:
            Code challenge value
        """
        if method == "plain":
            return code_verifier
        elif method == "S256":
            hash_bytes = hashlib.sha256(code_verifier.encode()).digest()
            return base64.urlsafe_b64encode(hash_bytes).decode('utf-8').rstrip('=')
        else:
            raise ValueError(f"Invalid code challenge method: {method}")

    def register_client(self, client: OAuthClient) -> Tuple[bool, Optional[str]]:
        """
        Register OAuth client.

        Args:
            client: OAuthClient instance

        Returns:
            Tuple of (success, error_message)
        """
        # Validate client configuration
        if not client.client_id:
            return False, "client_id is required"

        if client.client_id in self._clients:
            return False, f"client_id '{client.client_id}' already registered"

        if not client.redirect_uris:
            return False, "At least one redirect_uri is required"

        # Register client
        self._clients[client.client_id] = client

        self.logger.info(
            f"OAuth client registered",
            extra={"client_id": client.client_id, "client_name": client.client_name}
        )

        return True, None

    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """Get registered OAuth client"""
        return self._clients.get(client_id)

    def authenticate_client(
        self,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Authenticate OAuth client.

        Args:
            client_id: Client ID
            client_secret: Client secret (required for confidential clients)

        Returns:
            Tuple of (is_authenticated, error_message)
        """
        client = self.get_client(client_id)
        if not client:
            return False, "invalid_client"

        if client.is_confidential:
            if not client_secret:
                return False, "client_secret is required"

            if client_secret != client.client_secret:
                self.logger.warning(
                    f"Client authentication failed - invalid secret",
                    extra={"client_id": client_id}
                )
                return False, "invalid_client"

        # Update last used time
        client.last_used_at = datetime.utcnow()

        return True, None

    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = PKCE_CODE_CHALLENGE_METHOD,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Create authorization code.

        Args:
            client_id: Client ID
            user_id: User ID granting authorization
            redirect_uri: Redirect URI
            scope: Granted scopes
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method

        Returns:
            Tuple of (code, error_message)
        """
        client = self.get_client(client_id)
        if not client:
            return None, "invalid_client"

        if not client.validate_redirect_uri(redirect_uri):
            return None, "invalid_redirect_uri"

        if not client.validate_scope(scope):
            return None, "invalid_scope"

        # Generate authorization code
        code = self.generate_authorization_code()
        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        self._authorization_codes[code] = auth_code

        self.logger.info(
            f"Authorization code created",
            extra={"client_id": client_id, "user_id": user_id, "scope": scope}
        )

        return code, None

    def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code
            client_id: Client ID
            redirect_uri: Redirect URI (must match original)
            code_verifier: PKCE code verifier

        Returns:
            Tuple of (token_response_dict, error_message)
        """
        auth_code = self._authorization_codes.get(code)

        # Validate authorization code
        if not auth_code:
            return None, "invalid_code"

        if auth_code.is_expired():
            return None, "code_expired"

        if auth_code.is_used:
            # Possible token reuse attack
            self.logger.warning(
                f"Authorization code reuse detected",
                extra={"client_id": client_id, "code": code[:10]}
            )
            return None, "invalid_code"

        if auth_code.client_id != client_id:
            return None, "invalid_client"

        if auth_code.redirect_uri != redirect_uri:
            return None, "invalid_request"

        # Validate PKCE
        if auth_code.code_challenge:
            if not code_verifier:
                return None, "invalid_request"

            if not auth_code.validate_pkce(code_verifier):
                return None, "invalid_request"

        # Mark code as used
        auth_code.is_used = True

        # Create tokens
        now = datetime.utcnow()

        access_token = OAuthToken(
            token_type="access",
            token_value=self.generate_access_token(),
            client_id=client_id,
            user_id=auth_code.user_id,
            scope=auth_code.scope,
            issued_at=now,
            expires_in_seconds=OAUTH_ACCESS_TOKEN_TTL_SECONDS,
            refresh_token=self.generate_refresh_token(),
        )

        id_token = self.create_id_token(
            client_id=client_id,
            user_id=auth_code.user_id,
            nonce=None,  # Would be from authorization request
        )

        refresh_token = access_token.refresh_token

        self._tokens[access_token.token_value] = access_token

        self.logger.info(
            f"Authorization code exchanged for tokens",
            extra={
                "client_id": client_id,
                "user_id": auth_code.user_id,
                "scope": auth_code.scope
            }
        )

        return {
            "access_token": access_token.token_value,
            "token_type": "Bearer",
            "expires_in": OAUTH_ACCESS_TOKEN_TTL_SECONDS,
            "refresh_token": refresh_token,
            "id_token": id_token,
            "scope": auth_code.scope,
        }, None

    def create_id_token(
        self,
        client_id: str,
        user_id: str,
        nonce: Optional[str] = None,
        additional_claims: Optional[Dict] = None,
    ) -> str:
        """
        Create OpenID Connect ID token (JWT).

        Args:
            client_id: Client ID
            user_id: User ID
            nonce: Nonce from authorization request (for replay attack prevention)
            additional_claims: Additional claims to include in token

        Returns:
            Encoded JWT token
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=OAUTH_ID_TOKEN_TTL_SECONDS)

        claims = {
            "iss": f"https://api.hyperfactory.com",  # Issuer
            "sub": user_id,  # Subject (user ID)
            "aud": client_id,  # Audience
            "exp": int(expires_at.timestamp()),  # Expiration time
            "iat": int(now.timestamp()),  # Issued at
            "auth_time": int(now.timestamp()),  # Authentication time
            "acr": "0",  # Authentication Context Class Reference
        }

        if nonce:
            claims["nonce"] = nonce

        if additional_claims:
            claims.update(additional_claims)

        # Sign token
        token = jwt.encode(
            claims,
            self.signing_secret,
            algorithm="HS256"
        )

        return token

    def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token value
            client_id: Client ID

        Returns:
            Tuple of (token_response_dict, error_message)
        """
        # Find token with this refresh_token
        token = None
        for t in self._tokens.values():
            if t.refresh_token == refresh_token and t.client_id == client_id:
                token = t
                break

        if not token:
            return None, "invalid_grant"

        if token.is_expired():
            return None, "invalid_grant"

        # Create new access token
        now = datetime.utcnow()
        new_access_token = OAuthToken(
            token_type="access",
            token_value=self.generate_access_token(),
            client_id=client_id,
            user_id=token.user_id,
            scope=token.scope,
            issued_at=now,
            expires_in_seconds=OAUTH_ACCESS_TOKEN_TTL_SECONDS,
            refresh_token=refresh_token,  # Reuse refresh token
        )

        self._tokens[new_access_token.token_value] = new_access_token

        self.logger.info(
            f"Access token refreshed",
            extra={"client_id": client_id, "user_id": token.user_id}
        )

        return {
            "access_token": new_access_token.token_value,
            "token_type": "Bearer",
            "expires_in": OAUTH_ACCESS_TOKEN_TTL_SECONDS,
            "scope": new_access_token.scope,
        }, None

    def validate_access_token(self, access_token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Validate access token.

        Args:
            access_token: Access token value

        Returns:
            Tuple of (token_info_dict, error_message)
        """
        token = self._tokens.get(access_token)

        if not token:
            return None, "invalid_token"

        if token.is_expired():
            return None, "expired_token"

        return {
            "client_id": token.client_id,
            "user_id": token.user_id,
            "scope": token.scope,
            "expires_in": token.get_remaining_lifetime(),
        }, None

    def verify_id_token(self, id_token: str, client_id: str, nonce: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Verify and decode OpenID Connect ID token.

        Args:
            id_token: ID token (JWT)
            client_id: Expected client ID
            nonce: Expected nonce (for replay attack prevention)

        Returns:
            Tuple of (claims_dict, error_message)
        """
        try:
            claims = jwt.decode(
                id_token,
                self.signing_secret,
                algorithms=["HS256"],
                options={"verify_exp": True}  # Explicitly verify expiration
            )
        except jwt.ExpiredSignatureError:
            return None, "expired_token"
        except jwt.InvalidTokenError as e:
            return None, f"invalid_token: {str(e)}"

        # Validate claims
        if claims.get("aud") != client_id:
            return None, "invalid_aud"

        if nonce and claims.get("nonce") != nonce:
            return None, "invalid_nonce"

        return claims, None


# Global OAuth provider instance
oauth_provider = OAuthProviderManager()
