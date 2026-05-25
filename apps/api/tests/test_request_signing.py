"""Request Signing tests - Cryptographic request authentication"""

import pytest
import hmac
import hashlib
from datetime import datetime, timedelta
from app.request_signing import (
    RequestSigningManager,
    request_signing_manager,
    SIGNATURE_VERSION,
)


# ============================================================================
# Signature Generation Tests
# ============================================================================

def test_generate_signature_basic():
    """Test generating basic signature"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)

    assert signature.startswith(f"{SIGNATURE_VERSION}:")
    assert len(signature) > 10


def test_generate_signature_deterministic():
    """Test signature generation is deterministic"""
    secret = "secret123"
    body = b"request body"
    timestamp = "2024-01-15T10:30:00"

    sig1 = RequestSigningManager.generate_signature(secret, body, timestamp)
    sig2 = RequestSigningManager.generate_signature(secret, body, timestamp)

    assert sig1 == sig2


def test_generate_signature_with_nonce():
    """Test signature generation with nonce"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()
    nonce = "abc123def456"

    signature = RequestSigningManager.generate_signature(
        secret, body, timestamp, nonce
    )

    assert signature.startswith(f"{SIGNATURE_VERSION}:")


def test_generate_signature_string_body():
    """Test signature generation with string body"""
    secret = "secret123"
    body = "request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)

    assert signature.startswith(f"{SIGNATURE_VERSION}:")


def test_generate_signature_json_body():
    """Test signature generation with JSON body"""
    secret = "secret123"
    body = b'{"user": "test", "action": "create"}'
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)

    assert signature.startswith(f"{SIGNATURE_VERSION}:")


def test_generate_signature_different_secrets():
    """Test signatures differ with different secrets"""
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    sig1 = RequestSigningManager.generate_signature("secret1", body, timestamp)
    sig2 = RequestSigningManager.generate_signature("secret2", body, timestamp)

    assert sig1 != sig2


def test_generate_signature_different_bodies():
    """Test signatures differ with different bodies"""
    secret = "secret123"
    timestamp = datetime.utcnow().isoformat()

    sig1 = RequestSigningManager.generate_signature(secret, b"body1", timestamp)
    sig2 = RequestSigningManager.generate_signature(secret, b"body2", timestamp)

    assert sig1 != sig2


def test_generate_signature_different_timestamps():
    """Test signatures differ with different timestamps"""
    secret = "secret123"
    body = b"request body"

    sig1 = RequestSigningManager.generate_signature(secret, body, "2024-01-15T10:00:00")
    sig2 = RequestSigningManager.generate_signature(secret, body, "2024-01-15T10:01:00")

    assert sig1 != sig2


# ============================================================================
# Signature Verification Tests
# ============================================================================

def test_verify_signature_valid():
    """Test verifying valid signature"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)

    is_valid = RequestSigningManager.verify_signature(
        secret, body, signature, timestamp
    )

    assert is_valid is True


def test_verify_signature_invalid():
    """Test verifying invalid signature"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    is_valid = RequestSigningManager.verify_signature(
        secret, body, "1:invalidsignature", timestamp
    )

    assert is_valid is False


def test_verify_signature_modified_body():
    """Test signature fails with modified body"""
    secret = "secret123"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, b"body1", timestamp)

    is_valid = RequestSigningManager.verify_signature(
        secret, b"body2", signature, timestamp
    )

    assert is_valid is False


def test_verify_signature_wrong_secret():
    """Test signature fails with wrong secret"""
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature("secret1", body, timestamp)

    is_valid = RequestSigningManager.verify_signature("secret2", body, signature, timestamp)

    assert is_valid is False


def test_verify_signature_wrong_timestamp():
    """Test signature fails with wrong timestamp"""
    secret = "secret123"
    body = b"request body"

    signature = RequestSigningManager.generate_signature(secret, body, "2024-01-15T10:00:00")

    is_valid = RequestSigningManager.verify_signature(
        secret, body, signature, "2024-01-15T10:01:00"
    )

    assert is_valid is False


def test_verify_signature_with_nonce():
    """Test verifying signature with nonce"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()
    nonce = "abc123def456"

    signature = RequestSigningManager.generate_signature(
        secret, body, timestamp, nonce
    )

    is_valid = RequestSigningManager.verify_signature(
        secret, body, signature, timestamp, nonce
    )

    assert is_valid is True


def test_verify_signature_nonce_mismatch():
    """Test signature fails with nonce mismatch"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(
        secret, body, timestamp, "nonce1"
    )

    is_valid = RequestSigningManager.verify_signature(
        secret, body, signature, timestamp, "nonce2"
    )

    assert is_valid is False


def test_verify_signature_missing():
    """Test verification fails with missing signature"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    is_valid = RequestSigningManager.verify_signature(secret, body, "", timestamp)

    assert is_valid is False


def test_verify_signature_wrong_version():
    """Test verification fails with wrong version"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)
    # Modify version
    bad_signature = "2:" + signature.split(":", 1)[1]

    is_valid = RequestSigningManager.verify_signature(
        secret, body, bad_signature, timestamp
    )

    assert is_valid is False


def test_verify_signature_timing_attack_resistant():
    """Test signature verification is timing-attack resistant"""
    secret = "secret123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    signature = RequestSigningManager.generate_signature(secret, body, timestamp)
    wrong_sig1 = signature[:-1] + "0"  # Off by 1 char
    wrong_sig2 = signature[:-1] + "1"  # Off by 1 char, different

    # Both should return False (no timing difference expected)
    result1 = RequestSigningManager.verify_signature(
        secret, body, wrong_sig1, timestamp
    )
    result2 = RequestSigningManager.verify_signature(
        secret, body, wrong_sig2, timestamp
    )

    assert result1 is False
    assert result2 is False


# ============================================================================
# Timestamp Validation Tests
# ============================================================================

def test_validate_timestamp_valid():
    """Test validating recent timestamp"""
    manager = RequestSigningManager()
    timestamp = datetime.utcnow().isoformat()

    is_valid, error = manager.validate_timestamp(timestamp)

    assert is_valid is True
    assert error is None


def test_validate_timestamp_missing():
    """Test validating missing timestamp"""
    manager = RequestSigningManager()

    is_valid, error = manager.validate_timestamp("")

    assert is_valid is False
    assert error is not None


def test_validate_timestamp_future():
    """Test validating future timestamp (replay protection)"""
    manager = RequestSigningManager()
    future = (datetime.utcnow() + timedelta(minutes=1)).isoformat()

    is_valid, error = manager.validate_timestamp(future)

    assert is_valid is False
    assert "future" in error.lower()


def test_validate_timestamp_expired():
    """Test validating expired timestamp"""
    manager = RequestSigningManager(timestamp_max_age_seconds=10)
    old = (datetime.utcnow() - timedelta(seconds=20)).isoformat()

    is_valid, error = manager.validate_timestamp(old)

    assert is_valid is False
    assert "too old" in error.lower()


def test_validate_timestamp_at_limit():
    """Test validating timestamp at age limit"""
    manager = RequestSigningManager(timestamp_max_age_seconds=60)
    old = (datetime.utcnow() - timedelta(seconds=59)).isoformat()

    is_valid, error = manager.validate_timestamp(old)

    assert is_valid is True


def test_validate_timestamp_custom_max_age():
    """Test timestamp validation with custom max age"""
    manager = RequestSigningManager(timestamp_max_age_seconds=100)
    old = (datetime.utcnow() - timedelta(seconds=50)).isoformat()

    is_valid, error = manager.validate_timestamp(old, max_age_seconds=30)

    assert is_valid is False


def test_validate_timestamp_invalid_format():
    """Test validating timestamp with invalid format"""
    manager = RequestSigningManager()

    is_valid, error = manager.validate_timestamp("invalid")

    assert is_valid is False
    assert "invalid" in error.lower()


# ============================================================================
# Nonce Validation Tests
# ============================================================================

def test_validate_nonce_valid():
    """Test validating valid nonce"""
    manager = RequestSigningManager()
    nonce = "abc123def456789012345"  # Valid hex

    is_valid, error = manager.validate_nonce(nonce)

    assert is_valid is True
    assert error is None


def test_validate_nonce_missing():
    """Test validating missing nonce"""
    manager = RequestSigningManager()

    is_valid, error = manager.validate_nonce("")

    assert is_valid is False


def test_validate_nonce_too_short():
    """Test nonce too short"""
    manager = RequestSigningManager()

    is_valid, error = manager.validate_nonce("abc123")

    assert is_valid is False
    assert "short" in error.lower()


def test_validate_nonce_too_long():
    """Test nonce too long"""
    manager = RequestSigningManager()
    nonce = "a" * 256

    is_valid, error = manager.validate_nonce(nonce)

    assert is_valid is False
    assert "long" in error.lower()


def test_validate_nonce_non_hex():
    """Test nonce with non-hex characters"""
    manager = RequestSigningManager()
    nonce = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"  # Not valid hex

    is_valid, error = manager.validate_nonce(nonce)

    assert is_valid is False


def test_validate_nonce_non_string():
    """Test nonce with non-string type"""
    manager = RequestSigningManager()

    is_valid, error = manager.validate_nonce(12345)

    assert is_valid is False


def test_generate_nonce():
    """Test nonce generation"""
    manager = RequestSigningManager()

    nonce = manager.generate_nonce()

    assert isinstance(nonce, str)
    assert len(nonce) == 64
    # Should be valid hex
    is_valid, _ = manager.validate_nonce(nonce)
    assert is_valid is True


def test_generate_nonce_uniqueness():
    """Test generated nonces are unique"""
    manager = RequestSigningManager()

    nonces = set(manager.generate_nonce() for _ in range(100))

    assert len(nonces) == 100


# ============================================================================
# Component Extraction Tests
# ============================================================================

def test_extract_signature_components_valid():
    """Test extracting valid signature components"""
    manager = RequestSigningManager()
    sig = "1:abcd1234"
    ts = datetime.utcnow().isoformat()

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components(sig, ts)

    assert sig_out == sig
    assert ts_out == ts
    assert nonce_out is None
    assert error is None


def test_extract_signature_components_missing_signature():
    """Test extraction fails with missing signature"""
    manager = RequestSigningManager()
    ts = datetime.utcnow().isoformat()

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components(None, ts)

    assert error is not None
    assert "signature" in error.lower()


def test_extract_signature_components_missing_timestamp():
    """Test extraction fails with missing timestamp"""
    manager = RequestSigningManager()

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components("1:abcd", None)

    assert error is not None
    assert "timestamp" in error.lower()


def test_extract_signature_components_invalid_timestamp():
    """Test extraction fails with invalid timestamp"""
    manager = RequestSigningManager()

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components(
        "1:abcd", "invalid"
    )

    assert error is not None


def test_extract_signature_components_with_nonce():
    """Test extracting components with nonce"""
    manager = RequestSigningManager()
    sig = "1:abcd1234"
    ts = datetime.utcnow().isoformat()
    nonce = "abc123def456789012345"

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components(sig, ts, nonce)

    assert sig_out == sig
    assert ts_out == ts
    assert nonce_out == nonce
    assert error is None


def test_extract_signature_components_invalid_nonce():
    """Test extraction fails with invalid nonce"""
    manager = RequestSigningManager()
    sig = "1:abcd1234"
    ts = datetime.utcnow().isoformat()

    sig_out, ts_out, nonce_out, error = manager.extract_signature_components(
        sig, ts, "invalid"
    )

    assert error is not None


# ============================================================================
# Integration Tests
# ============================================================================

def test_manager_instance_exists():
    """Test global manager instance exists"""
    assert request_signing_manager is not None
    assert isinstance(request_signing_manager, RequestSigningManager)


def test_typical_request_signing_flow():
    """Test typical request signing flow"""
    secret = "api_secret_key_123"
    request_body = b'{"action": "create", "data": {"name": "test"}}'
    timestamp = datetime.utcnow().isoformat()
    nonce = RequestSigningManager.generate_nonce()

    # Client signs request
    signature = RequestSigningManager.generate_signature(
        secret, request_body, timestamp, nonce
    )

    # Server verifies request
    is_valid = RequestSigningManager.verify_signature(
        secret, request_body, signature, timestamp, nonce
    )

    assert is_valid is True


def test_replay_attack_prevention():
    """Test protection against replay attacks"""
    manager = RequestSigningManager(timestamp_max_age_seconds=10)
    secret = "api_secret_key_123"
    body = b"request body"

    # Generate signature with timestamp from 30 seconds ago
    old_timestamp = (datetime.utcnow() - timedelta(seconds=30)).isoformat()
    signature = RequestSigningManager.generate_signature(secret, body, old_timestamp)

    # Verify timestamp is rejected
    ts_valid, ts_error = manager.validate_timestamp(old_timestamp)

    assert ts_valid is False
    assert "too old" in ts_error.lower()


def test_request_tampering_detection():
    """Test detection of tampered requests"""
    secret = "api_secret_key_123"
    timestamp = datetime.utcnow().isoformat()

    # Original request
    original_body = b'{"amount": 100}'
    signature = RequestSigningManager.generate_signature(secret, original_body, timestamp)

    # Tampered request
    tampered_body = b'{"amount": 1000}'

    # Verification fails
    is_valid = RequestSigningManager.verify_signature(
        secret, tampered_body, signature, timestamp
    )

    assert is_valid is False


def test_man_in_middle_attack_prevention():
    """Test MITM attack prevention"""
    secret = "api_secret_key_123"
    body = b"request body"
    timestamp = datetime.utcnow().isoformat()

    # Legitimate signature
    signature = RequestSigningManager.generate_signature(secret, body, timestamp)

    # Attacker tries to forge signature with wrong secret
    attacker_secret = "attacker_secret"
    forged = RequestSigningManager.generate_signature(attacker_secret, body, timestamp)

    # Forgery is detected
    is_valid = RequestSigningManager.verify_signature(secret, body, forged, timestamp)

    assert is_valid is False


def test_idempotency_with_nonce():
    """Test nonce enables idempotent requests"""
    secret = "api_secret_key_123"
    body = b'{"action": "transfer", "amount": 100}'
    timestamp = datetime.utcnow().isoformat()
    request_id = RequestSigningManager.generate_nonce()

    # Create request with nonce
    signature = RequestSigningManager.generate_signature(
        secret, body, timestamp, request_id
    )

    # Server can verify request came from same client
    is_valid = RequestSigningManager.verify_signature(
        secret, body, signature, timestamp, request_id
    )

    assert is_valid is True

    # Same nonce + body = same signature (idempotent)
    signature2 = RequestSigningManager.generate_signature(
        secret, body, timestamp, request_id
    )

    assert signature == signature2


def test_different_resources_different_signatures():
    """Test signatures differ for different endpoints"""
    secret = "api_secret_key_123"
    timestamp = datetime.utcnow().isoformat()

    # Create resource
    sig_create = RequestSigningManager.generate_signature(
        secret, b'{"action": "create"}', timestamp
    )

    # Update resource
    sig_update = RequestSigningManager.generate_signature(
        secret, b'{"action": "update"}', timestamp
    )

    assert sig_create != sig_update
