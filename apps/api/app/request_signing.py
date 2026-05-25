"""Request Signing - Cryptographic request authentication and integrity verification"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.models import APIKey
import secrets
import logging

# Configuration
REQUEST_SIGNATURE_ALGORITHM = "HMAC-SHA256"
DEFAULT_TIMESTAMP_MAX_AGE_SECONDS = 300  # 5 minutes
SIGNATURE_VERSION = "1"
SIGNATURE_HEADER_FORMAT = f"{SIGNATURE_VERSION}:{{}}"  # "1:signature_hex"


class RequestSigningManager:
    """Manages cryptographic request signing and verification"""

    def __init__(
        self,
        timestamp_max_age_seconds: int = DEFAULT_TIMESTAMP_MAX_AGE_SECONDS,
    ):
        """
        Initialize request signing manager.

        Args:
            timestamp_max_age_seconds: Maximum age of timestamp (prevents replay)
        """
        self.timestamp_max_age_seconds = timestamp_max_age_seconds
        self.logger = logging.getLogger("request_signing")

    @staticmethod
    def generate_signature(
        api_key_secret: str,
        request_body: bytes,
        timestamp: str,
        nonce: Optional[str] = None,
    ) -> str:
        """
        Generate HMAC-SHA256 signature for request.

        Args:
            api_key_secret: API key secret (private)
            request_body: Request body bytes
            timestamp: ISO 8601 timestamp
            nonce: Optional unique request ID

        Returns:
            Signature in format "1:hex_signature"
        """
        # Ensure body is bytes
        if isinstance(request_body, str):
            request_body = request_body.encode("utf-8")

        # Build signing string
        if nonce:
            signing_string = f"{timestamp}:{nonce}:{request_body.decode('utf-8', errors='replace')}"
        else:
            signing_string = f"{timestamp}:{request_body.decode('utf-8', errors='replace')}"

        # Generate HMAC-SHA256
        signature_hex = hmac.new(
            api_key_secret.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return SIGNATURE_HEADER_FORMAT.format(signature_hex)

    @staticmethod
    def verify_signature(
        api_key_secret: str,
        request_body: bytes,
        signature: str,
        timestamp: str,
        nonce: Optional[str] = None,
    ) -> bool:
        """
        Verify HMAC-SHA256 signature for request.

        Args:
            api_key_secret: API key secret (private)
            request_body: Request body bytes
            signature: Signature header value
            timestamp: ISO 8601 timestamp
            nonce: Optional unique request ID

        Returns:
            True if signature is valid
        """
        if not signature:
            return False

        # Parse signature header
        try:
            parts = signature.split(":", 1)
            if len(parts) != 2:
                return False

            version, sig_hex = parts
            if version != SIGNATURE_VERSION:
                return False
        except (ValueError, IndexError):
            return False

        # Generate expected signature
        expected_signature = RequestSigningManager.generate_signature(
            api_key_secret, request_body, timestamp, nonce
        )

        # Extract expected hex
        expected_parts = expected_signature.split(":", 1)
        expected_hex = expected_parts[1] if len(expected_parts) == 2 else ""

        # Compare using constant-time comparison (prevent timing attacks)
        return hmac.compare_digest(sig_hex, expected_hex)

    def validate_timestamp(
        self,
        timestamp: str,
        max_age_seconds: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate timestamp freshness (prevent replay attacks).

        Args:
            timestamp: ISO 8601 timestamp
            max_age_seconds: Override default max age

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not timestamp:
            return False, "Missing timestamp"

        max_age = max_age_seconds or self.timestamp_max_age_seconds

        try:
            # Parse ISO 8601 timestamp
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.utcnow()

            # Check if timestamp is in the future
            if ts > now:
                return False, "Timestamp is in the future"

            # Check if timestamp is too old
            age = (now - ts).total_seconds()
            if age > max_age:
                return (
                    False,
                    f"Timestamp is too old (age: {age:.0f}s, max: {max_age}s)",
                )

            return True, None
        except (ValueError, TypeError) as e:
            return False, f"Invalid timestamp format: {str(e)}"

    def validate_nonce(
        self,
        nonce: str,
        max_age_seconds: int = 86400,  # 24 hours
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate nonce format (idempotency key).

        Note: Full deduplication requires nonce storage. This validates format only.

        Args:
            nonce: Nonce/request ID
            max_age_seconds: Max age for nonce (storage-dependent)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not nonce:
            return False, "Missing nonce"

        # Validate format: hex string
        if not isinstance(nonce, str):
            return False, "Nonce must be string"

        if len(nonce) < 16:
            return False, "Nonce too short (min 16 chars)"

        if len(nonce) > 128:
            return False, "Nonce too long (max 128 chars)"

        # Verify it's valid hex
        try:
            int(nonce, 16)
            return True, None
        except ValueError:
            return False, "Nonce must be valid hex string"

    @staticmethod
    def generate_nonce() -> str:
        """Generate random nonce (idempotency key)."""
        return secrets.token_hex(32)  # 64-char hex string

    def extract_signature_components(
        self,
        signature_header: Optional[str],
        timestamp_header: Optional[str],
        nonce_header: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract and validate signature component headers.

        Args:
            signature_header: X-Signature header value
            timestamp_header: X-Timestamp header value
            nonce_header: X-Nonce header value

        Returns:
            Tuple of (signature, timestamp, nonce, error_message)
        """
        errors = []

        if not signature_header:
            errors.append("Missing X-Signature header")

        if not timestamp_header:
            errors.append("Missing X-Timestamp header")

        if errors:
            return None, None, None, "; ".join(errors)

        # Validate timestamp format
        ts_valid, ts_error = self.validate_timestamp(timestamp_header)
        if not ts_valid:
            return None, None, None, ts_error

        # Validate nonce if present
        if nonce_header:
            nonce_valid, nonce_error = self.validate_nonce(nonce_header)
            if not nonce_valid:
                return None, None, None, nonce_error

        return signature_header, timestamp_header, nonce_header, None

    def log_signature_verification(
        self,
        api_key_id: str,
        is_valid: bool,
        error: Optional[str] = None,
        request_path: Optional[str] = None,
        source_ip: Optional[str] = None,
    ) -> None:
        """
        Log signature verification attempt (security audit).

        Args:
            api_key_id: API key ID
            is_valid: Whether signature was valid
            error: Error message if verification failed
            request_path: Request path for context
            source_ip: Source IP for audit
        """
        status = "VERIFIED" if is_valid else "FAILED"
        log_msg = f"Signature verification {status} for key={api_key_id}"

        if request_path:
            log_msg += f" path={request_path}"
        if source_ip:
            log_msg += f" ip={source_ip}"
        if error:
            log_msg += f" error={error}"

        if is_valid:
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)


# Global request signing manager instance
request_signing_manager = RequestSigningManager()
