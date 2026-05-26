"""Webhook Management tests - Event-driven delivery with signing and retry logic"""

import pytest
import json
from datetime import datetime, timedelta
from app.webhook_manager import (
    WebhookEvent,
    WebhookEventStatus,
    WebhookDeliveryStatus,
    WebhookPayload,
    WebhookDeliveryAttempt,
    Webhook,
    WebhookManager,
    webhook_manager,
)


# ============================================================================
# WebhookEvent & WebhookPayload Tests
# ============================================================================

def test_webhook_event_factory_events():
    """Test factory webhook events"""
    assert WebhookEvent.FACTORY_CREATED == "factory.created"
    assert WebhookEvent.FACTORY_UPDATED == "factory.updated"
    assert WebhookEvent.FACTORY_DELETED == "factory.deleted"


def test_webhook_event_machine_events():
    """Test machine webhook events"""
    assert WebhookEvent.MACHINE_CREATED == "machine.created"
    assert WebhookEvent.MACHINE_UPDATED == "machine.updated"
    assert WebhookEvent.MACHINE_DELETED == "machine.deleted"


def test_webhook_event_job_events():
    """Test job webhook events"""
    assert WebhookEvent.JOB_CREATED == "job.created"
    assert WebhookEvent.JOB_STARTED == "job.started"
    assert WebhookEvent.JOB_COMPLETED == "job.completed"
    assert WebhookEvent.JOB_FAILED == "job.failed"


def test_webhook_event_cad_events():
    """Test CAD analysis webhook events"""
    assert WebhookEvent.CAD_ANALYSIS_COMPLETED == "cad.analysis_completed"
    assert WebhookEvent.CAD_ANALYSIS_FAILED == "cad.analysis_failed"


def test_webhook_event_user_events():
    """Test user and API key webhook events"""
    assert WebhookEvent.USER_CREATED == "user.created"
    assert WebhookEvent.USER_UPDATED == "user.updated"
    assert WebhookEvent.API_KEY_CREATED == "api_key.created"
    assert WebhookEvent.API_KEY_REVOKED == "api_key.revoked"


def test_webhook_payload_creation():
    """Test webhook payload creation"""
    data = {"factory_id": "123", "name": "Test Factory"}
    payload = WebhookPayload(
        event=WebhookEvent.FACTORY_CREATED.value,
        created_at=datetime.utcnow().isoformat(),
        data=data,
    )

    assert payload.event == "factory.created"
    assert payload.data == data
    assert payload.version == "1.0"


def test_webhook_payload_to_json():
    """Test webhook payload JSON serialization"""
    data = {"id": "123"}
    payload = WebhookPayload(
        event="factory.created",
        created_at="2024-01-15T10:30:00",
        data=data,
    )

    json_str = payload.to_json()
    parsed = json.loads(json_str)

    assert parsed["event"] == "factory.created"
    assert parsed["data"] == data
    assert parsed["version"] == "1.0"


# ============================================================================
# WebhookDeliveryAttempt Tests
# ============================================================================

def test_delivery_attempt_creation():
    """Test delivery attempt initialization"""
    attempt = WebhookDeliveryAttempt(
        webhook_id="webhook123",
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
    )

    assert attempt.webhook_id == "webhook123"
    assert attempt.attempt_number == 1
    assert attempt.status == WebhookDeliveryStatus.SUCCESS
    assert attempt.id is not None
    assert len(attempt.id) > 0
    assert attempt.timestamp is not None


def test_delivery_attempt_with_http_status():
    """Test delivery attempt with HTTP status code"""
    attempt = WebhookDeliveryAttempt(
        webhook_id="webhook123",
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
    )
    attempt.http_status_code = 200
    attempt.response_time_ms = 150

    assert attempt.http_status_code == 200
    assert attempt.response_time_ms == 150


def test_delivery_attempt_failed_with_error():
    """Test delivery attempt with error message"""
    attempt = WebhookDeliveryAttempt(
        webhook_id="webhook123",
        attempt_number=2,
        status=WebhookDeliveryStatus.FAILED,
    )
    attempt.http_status_code = 500
    attempt.error_message = "Internal Server Error"

    assert attempt.status == WebhookDeliveryStatus.FAILED
    assert attempt.error_message == "Internal Server Error"


def test_delivery_attempt_timeout():
    """Test delivery attempt timeout status"""
    attempt = WebhookDeliveryAttempt(
        webhook_id="webhook123",
        attempt_number=3,
        status=WebhookDeliveryStatus.TIMEOUT,
    )
    attempt.error_message = "Request timeout after 30s"

    assert attempt.status == WebhookDeliveryStatus.TIMEOUT


# ============================================================================
# Webhook Subscription Tests
# ============================================================================

def test_webhook_creation():
    """Test webhook subscription creation"""
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        secret="secret_key_xyz",
    )

    assert webhook.webhook_id == "webhook123"
    assert webhook.user_id == "user456"
    assert webhook.url == "https://example.com/webhook"
    assert webhook.events == [WebhookEvent.FACTORY_CREATED]
    assert webhook.secret == "secret_key_xyz"
    assert webhook.is_active is True
    assert webhook.failure_count == 0
    assert webhook.consecutive_failures == 0


def test_webhook_matches_event():
    """Test webhook event matching"""
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED, WebhookEvent.FACTORY_UPDATED],
        secret="secret",
    )

    assert webhook.matches_event(WebhookEvent.FACTORY_CREATED) is True
    assert webhook.matches_event(WebhookEvent.FACTORY_UPDATED) is True
    assert webhook.matches_event(WebhookEvent.FACTORY_DELETED) is False
    assert webhook.matches_event(WebhookEvent.JOB_CREATED) is False


def test_webhook_custom_headers():
    """Test webhook custom headers"""
    headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        secret="secret",
        custom_headers=headers,
    )

    assert webhook.custom_headers == headers


def test_webhook_disable_after_failures():
    """Test webhook disable on consecutive failures threshold"""
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        secret="secret",
    )

    # Increment to just below threshold
    for _ in range(9):
        webhook.increment_failure_count()

    assert webhook.is_active is True
    assert webhook.disable_after_failures(threshold=10) is False

    # Reach threshold
    webhook.increment_failure_count()
    assert webhook.disable_after_failures(threshold=10) is True
    assert webhook.is_active is False


def test_webhook_reset_failure_count():
    """Test failure count reset on success"""
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        secret="secret",
    )

    webhook.increment_failure_count()
    webhook.increment_failure_count()
    assert webhook.consecutive_failures == 2

    webhook.reset_failure_count()
    assert webhook.consecutive_failures == 0


def test_webhook_increment_failure_count():
    """Test failure count increment"""
    webhook = Webhook(
        webhook_id="webhook123",
        user_id="user456",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        secret="secret",
    )

    webhook.increment_failure_count()
    assert webhook.failure_count == 1
    assert webhook.consecutive_failures == 1

    webhook.increment_failure_count()
    assert webhook.failure_count == 2
    assert webhook.consecutive_failures == 2


# ============================================================================
# WebhookManager CRUD Tests
# ============================================================================

def test_create_webhook():
    """Test webhook creation via manager"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    assert webhook_id is not None
    assert len(webhook_id) > 0
    assert secret is not None
    assert len(secret) > 0


def test_get_webhook():
    """Test retrieving webhook by ID"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    webhook = manager.get_webhook(webhook_id)
    assert webhook is not None
    assert webhook.webhook_id == webhook_id
    assert webhook.user_id == "user123"


def test_get_nonexistent_webhook():
    """Test retrieving non-existent webhook"""
    manager = WebhookManager()
    webhook = manager.get_webhook("nonexistent")
    assert webhook is None


def test_get_user_webhooks():
    """Test retrieving all webhooks for a user"""
    manager = WebhookManager()
    user_id = "user123"

    webhook_id1, _ = manager.create_webhook(
        user_id=user_id,
        url="https://example.com/webhook1",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    webhook_id2, _ = manager.create_webhook(
        user_id=user_id,
        url="https://example.com/webhook2",
        events=[WebhookEvent.FACTORY_UPDATED],
    )

    # Create webhook for different user
    manager.create_webhook(
        user_id="user456",
        url="https://example.com/webhook3",
        events=[WebhookEvent.JOB_CREATED],
    )

    user_webhooks = manager.get_user_webhooks(user_id)
    assert len(user_webhooks) == 2
    assert webhook_id1 in [w.webhook_id for w in user_webhooks]
    assert webhook_id2 in [w.webhook_id for w in user_webhooks]


def test_delete_webhook():
    """Test webhook deletion"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    assert manager.get_webhook(webhook_id) is not None
    assert manager.delete_webhook(webhook_id) is True
    assert manager.get_webhook(webhook_id) is None


def test_delete_nonexistent_webhook():
    """Test deleting non-existent webhook"""
    manager = WebhookManager()
    assert manager.delete_webhook("nonexistent") is False


def test_update_webhook():
    """Test webhook update"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    new_url = "https://example.com/new-webhook"
    new_events = [WebhookEvent.FACTORY_UPDATED, WebhookEvent.FACTORY_DELETED]

    assert manager.update_webhook(
        webhook_id,
        url=new_url,
        events=new_events,
    ) is True

    webhook = manager.get_webhook(webhook_id)
    assert webhook.url == new_url
    assert webhook.events == new_events


def test_update_webhook_is_active():
    """Test updating webhook active status"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    assert manager.get_webhook(webhook_id).is_active is True
    assert manager.update_webhook(webhook_id, is_active=False) is True
    assert manager.get_webhook(webhook_id).is_active is False


def test_update_nonexistent_webhook():
    """Test updating non-existent webhook"""
    manager = WebhookManager()
    assert manager.update_webhook("nonexistent", url="https://example.com") is False


# ============================================================================
# Event Queueing & Processing Tests
# ============================================================================

def test_enqueue_event():
    """Test event enqueueing"""
    manager = WebhookManager()
    data = {"factory_id": "123", "name": "Test Factory"}

    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, data)

    assert len(manager._events_queue) == 1
    event, event_data = manager._events_queue[0]
    assert event == WebhookEvent.FACTORY_CREATED
    assert event_data == data


def test_process_events_returns_count():
    """Test event processing returns count"""
    manager = WebhookManager()

    # Create webhook
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Enqueue multiple events
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "1"})
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "2"})

    processed = manager.process_events()
    assert processed == 2


def test_process_events_clears_queue():
    """Test event processing clears queue"""
    manager = WebhookManager()

    manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "1"})
    assert len(manager._events_queue) == 1

    manager.process_events()
    assert len(manager._events_queue) == 0


def test_process_events_matches_webhooks():
    """Test events only delivered to matching webhooks"""
    manager = WebhookManager()

    # Register a mock delivery hook that records successful attempts
    def mock_delivery_hook(webhook, payload):
        manager.record_delivery_attempt(
            webhook_id=webhook.webhook_id,
            attempt_number=1,
            status=WebhookDeliveryStatus.SUCCESS,
            http_status_code=200,
        )

    manager.register_delivery_hook(mock_delivery_hook)

    # Webhook that matches FACTORY_CREATED
    webhook_id1, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook1",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Webhook that doesn't match FACTORY_CREATED
    webhook_id2, _ = manager.create_webhook(
        user_id="user456",
        url="https://example.com/webhook2",
        events=[WebhookEvent.JOB_CREATED],
    )

    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "1"})
    manager.process_events()

    # Check that only the matching webhook recorded delivery
    webhook1 = manager.get_webhook(webhook_id1)
    webhook2 = manager.get_webhook(webhook_id2)

    assert len(webhook1.delivery_attempts) > 0
    assert len(webhook2.delivery_attempts) == 0


def test_process_events_no_matching_webhooks():
    """Test processing when no webhooks match"""
    manager = WebhookManager()

    manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.JOB_CREATED],
    )

    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "1"})
    # Process: event is removed from queue but no matching webhooks
    processed = manager.process_events()

    # Event counts as processed (no matching webhooks just means no deliveries)
    assert processed == 1
    assert len(manager._events_queue) == 0


# ============================================================================
# Signature Generation & Verification Tests
# ============================================================================

def test_sign_payload():
    """Test payload signing"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
        custom_headers={},
    )

    payload_json = '{"event": "factory.created", "data": {"id": "123"}}'
    signature = manager.sign_payload(webhook_id, payload_json)

    assert signature is not None
    assert signature.startswith("sha256=")
    assert len(signature) > 10


def test_sign_payload_consistency():
    """Test signature consistency for same payload"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    payload_json = '{"event": "factory.created"}'
    sig1 = manager.sign_payload(webhook_id, payload_json)
    sig2 = manager.sign_payload(webhook_id, payload_json)

    assert sig1 == sig2


def test_sign_payload_different_for_different_payloads():
    """Test signatures differ for different payloads"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    sig1 = manager.sign_payload(webhook_id, '{"event": "factory.created"}')
    sig2 = manager.sign_payload(webhook_id, '{"event": "factory.updated"}')

    assert sig1 != sig2


def test_sign_nonexistent_webhook():
    """Test signing for non-existent webhook"""
    manager = WebhookManager()
    signature = manager.sign_payload("nonexistent", '{"event": "test"}')
    assert signature is None


def test_verify_webhook_signature_valid():
    """Test verifying valid webhook signature"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    payload_json = '{"event": "factory.created"}'
    signature = manager.sign_payload(webhook_id, payload_json)

    is_valid, error = manager.verify_webhook_signature(
        webhook_id, signature, payload_json
    )

    assert is_valid is True
    assert error is None


def test_verify_webhook_signature_invalid():
    """Test verifying invalid webhook signature"""
    manager = WebhookManager()
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    payload_json = '{"event": "factory.created"}'
    wrong_signature = "sha256=invalid_signature_xyz"

    is_valid, error = manager.verify_webhook_signature(
        webhook_id, wrong_signature, payload_json
    )

    assert is_valid is False
    assert error == "invalid_signature"


def test_verify_signature_nonexistent_webhook():
    """Test verifying signature for non-existent webhook"""
    manager = WebhookManager()
    is_valid, error = manager.verify_webhook_signature(
        "nonexistent", "sha256=xyz", "{}"
    )

    assert is_valid is False
    assert error == "webhook_not_found"


# ============================================================================
# Delivery Attempt Recording Tests
# ============================================================================

def test_record_delivery_attempt():
    """Test recording delivery attempt"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    attempt_id = manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
        http_status_code=200,
        response_time_ms=150,
    )

    assert attempt_id is not None
    assert len(attempt_id) > 0

    webhook = manager.get_webhook(webhook_id)
    assert len(webhook.delivery_attempts) == 1
    assert webhook.delivery_attempts[0].id == attempt_id


def test_record_delivery_attempt_success_resets_failures():
    """Test successful delivery resets failure count"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    webhook = manager.get_webhook(webhook_id)
    webhook.increment_failure_count()
    webhook.increment_failure_count()
    assert webhook.consecutive_failures == 2

    manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=3,
        status=WebhookDeliveryStatus.SUCCESS,
        http_status_code=200,
    )

    webhook = manager.get_webhook(webhook_id)
    assert webhook.consecutive_failures == 0


def test_record_delivery_attempt_failure_increments_count():
    """Test failed delivery increments failure count"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=1,
        status=WebhookDeliveryStatus.FAILED,
        http_status_code=500,
        error_message="Server Error",
    )

    webhook = manager.get_webhook(webhook_id)
    assert webhook.failure_count == 1
    assert webhook.consecutive_failures == 1


def test_record_delivery_attempt_nonexistent_webhook():
    """Test recording attempt for non-existent webhook"""
    manager = WebhookManager()
    attempt_id = manager.record_delivery_attempt(
        webhook_id="nonexistent",
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
    )

    assert attempt_id == ""


def test_record_delivery_attempt_updates_last_triggered():
    """Test delivery attempt updates last_triggered_at"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    webhook = manager.get_webhook(webhook_id)
    assert webhook.last_triggered_at is None

    manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
    )

    webhook = manager.get_webhook(webhook_id)
    assert webhook.last_triggered_at is not None


# ============================================================================
# Delivery History & Statistics Tests
# ============================================================================

def test_get_delivery_history():
    """Test retrieving delivery history"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Record multiple attempts
    for i in range(1, 4):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=i,
            status=WebhookDeliveryStatus.SUCCESS if i % 2 == 0 else WebhookDeliveryStatus.FAILED,
            http_status_code=200 if i % 2 == 0 else 500,
        )

    history = manager.get_delivery_history(webhook_id)
    assert len(history) == 3


def test_get_delivery_history_limit():
    """Test delivery history respects limit"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Record 10 attempts
    for i in range(10):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=i + 1,
            status=WebhookDeliveryStatus.SUCCESS,
        )

    history = manager.get_delivery_history(webhook_id, limit=5)
    assert len(history) == 5


def test_get_delivery_history_nonexistent_webhook():
    """Test getting history for non-existent webhook"""
    manager = WebhookManager()
    history = manager.get_delivery_history("nonexistent")
    assert history == []


def test_get_webhook_stats():
    """Test webhook statistics calculation"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Record 3 successful, 2 failed
    for i in range(3):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=i + 1,
            status=WebhookDeliveryStatus.SUCCESS,
            response_time_ms=100 + i * 10,
        )

    for i in range(2):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=4 + i,
            status=WebhookDeliveryStatus.FAILED,
        )

    stats = manager.get_webhook_stats(webhook_id)

    assert stats["total_attempts"] == 5
    assert stats["successful"] == 3
    assert stats["failed"] == 2
    assert stats["success_rate"] == 0.6
    assert stats["is_active"] is True


def test_get_webhook_stats_avg_response_time():
    """Test webhook stats average response time calculation"""
    manager = WebhookManager()
    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=1,
        status=WebhookDeliveryStatus.SUCCESS,
        response_time_ms=100,
    )

    manager.record_delivery_attempt(
        webhook_id=webhook_id,
        attempt_number=2,
        status=WebhookDeliveryStatus.SUCCESS,
        response_time_ms=200,
    )

    stats = manager.get_webhook_stats(webhook_id)
    assert stats["avg_response_time_ms"] == 150.0


def test_get_webhook_stats_nonexistent_webhook():
    """Test getting stats for non-existent webhook"""
    manager = WebhookManager()
    stats = manager.get_webhook_stats("nonexistent")
    assert stats == {}


# ============================================================================
# Delivery Hook Registration Tests
# ============================================================================

def test_register_delivery_hook():
    """Test registering delivery hook"""
    manager = WebhookManager()

    hook_called = []

    def test_hook(webhook, payload):
        hook_called.append((webhook.webhook_id, payload.event))

    manager.register_delivery_hook(test_hook)
    assert len(manager._delivery_hooks) == 1


def test_multiple_delivery_hooks():
    """Test registering multiple delivery hooks"""
    manager = WebhookManager()

    def hook1(webhook, payload):
        pass

    def hook2(webhook, payload):
        pass

    manager.register_delivery_hook(hook1)
    manager.register_delivery_hook(hook2)

    assert len(manager._delivery_hooks) == 2


def test_delivery_hook_called_on_event_processing():
    """Test delivery hooks are called during event processing"""
    manager = WebhookManager()

    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    hook_calls = []

    def test_hook(webhook, payload):
        hook_calls.append((webhook.webhook_id, payload.event))

    manager.register_delivery_hook(test_hook)
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "123"})
    manager.process_events()

    assert len(hook_calls) == 1
    assert hook_calls[0][0] == webhook_id
    assert hook_calls[0][1] == "factory.created"


def test_delivery_hook_exception_handled():
    """Test delivery hook exception is handled gracefully"""
    manager = WebhookManager()

    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    def failing_hook(webhook, payload):
        raise Exception("Hook failed")

    manager.register_delivery_hook(failing_hook)
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "123"})

    # Should not raise, should handle gracefully
    processed = manager.process_events()
    assert processed == 1


# ============================================================================
# Token Generation Tests
# ============================================================================

def test_generate_webhook_id():
    """Test webhook ID generation"""
    manager = WebhookManager()
    webhook_id = manager.generate_webhook_id()

    assert webhook_id is not None
    assert len(webhook_id) > 0


def test_generate_webhook_id_randomness():
    """Test webhook ID randomness"""
    manager = WebhookManager()
    id1 = manager.generate_webhook_id()
    id2 = manager.generate_webhook_id()

    assert id1 != id2


def test_generate_secret():
    """Test secret generation"""
    manager = WebhookManager()
    secret = manager.generate_secret()

    assert secret is not None
    assert len(secret) > 0


def test_generate_secret_randomness():
    """Test secret randomness"""
    manager = WebhookManager()
    secret1 = manager.generate_secret()
    secret2 = manager.generate_secret()

    assert secret1 != secret2


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_webhook_workflow():
    """Test complete webhook lifecycle"""
    manager = WebhookManager()

    # Register mock delivery hook
    def mock_delivery_hook(webhook, payload):
        manager.record_delivery_attempt(
            webhook_id=webhook.webhook_id,
            attempt_number=1,
            status=WebhookDeliveryStatus.SUCCESS,
            http_status_code=200,
            response_time_ms=100,
        )

    manager.register_delivery_hook(mock_delivery_hook)

    # 1. Create webhook
    webhook_id, secret = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # 2. Enqueue event
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"factory_id": "f123", "name": "Factory 1"})

    # 3. Process events
    processed = manager.process_events()
    assert processed == 1

    # 4. Get webhook stats
    stats = manager.get_webhook_stats(webhook_id)
    assert stats["total_attempts"] >= 1


def test_multiple_users_separate_webhooks():
    """Test multiple users have separate webhook subscriptions"""
    manager = WebhookManager()

    webhook_id1, _ = manager.create_webhook(
        user_id="user1",
        url="https://example.com/webhook1",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    webhook_id2, _ = manager.create_webhook(
        user_id="user2",
        url="https://example.com/webhook2",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    user1_webhooks = manager.get_user_webhooks("user1")
    user2_webhooks = manager.get_user_webhooks("user2")

    assert len(user1_webhooks) == 1
    assert len(user2_webhooks) == 1
    assert user1_webhooks[0].webhook_id == webhook_id1
    assert user2_webhooks[0].webhook_id == webhook_id2


def test_event_filtering_by_subscription():
    """Test events are only delivered to webhooks that subscribe"""
    manager = WebhookManager()

    # Register mock delivery hook
    def mock_delivery_hook(webhook, payload):
        manager.record_delivery_attempt(
            webhook_id=webhook.webhook_id,
            attempt_number=1,
            status=WebhookDeliveryStatus.SUCCESS,
            http_status_code=200,
        )

    manager.register_delivery_hook(mock_delivery_hook)

    # User1 subscribes to FACTORY_CREATED
    webhook_id1, _ = manager.create_webhook(
        user_id="user1",
        url="https://example.com/webhook1",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # User2 subscribes to JOB_CREATED
    webhook_id2, _ = manager.create_webhook(
        user_id="user2",
        url="https://example.com/webhook2",
        events=[WebhookEvent.JOB_CREATED],
    )

    # Send FACTORY_CREATED event
    manager.enqueue_event(WebhookEvent.FACTORY_CREATED, {"id": "f1"})
    manager.process_events()

    webhook1 = manager.get_webhook(webhook_id1)
    webhook2 = manager.get_webhook(webhook_id2)

    # Only webhook1 should have delivery attempts
    assert len(webhook1.delivery_attempts) > 0
    assert len(webhook2.delivery_attempts) == 0


def test_webhook_failure_cascading():
    """Test failure tracking and auto-disable"""
    manager = WebhookManager()

    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Simulate 10 consecutive failures
    for i in range(10):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=i + 1,
            status=WebhookDeliveryStatus.FAILED,
            http_status_code=500,
        )

    webhook = manager.get_webhook(webhook_id)
    assert webhook.is_active is False
    assert webhook.consecutive_failures == 10


def test_webhook_stats_after_multiple_attempts():
    """Test webhook statistics after multiple delivery attempts"""
    manager = WebhookManager()

    webhook_id, _ = manager.create_webhook(
        user_id="user123",
        url="https://example.com/webhook",
        events=[WebhookEvent.FACTORY_CREATED],
    )

    # Record 7 successful, 3 failed
    for i in range(7):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=i + 1,
            status=WebhookDeliveryStatus.SUCCESS,
            response_time_ms=100,
        )

    for i in range(3):
        manager.record_delivery_attempt(
            webhook_id=webhook_id,
            attempt_number=8 + i,
            status=WebhookDeliveryStatus.FAILED,
            http_status_code=500,
        )

    stats = manager.get_webhook_stats(webhook_id)

    assert stats["total_attempts"] == 10
    assert stats["successful"] == 7
    assert stats["failed"] == 3
    assert stats["success_rate"] == 0.7


def test_global_webhook_manager_instance():
    """Test global webhook manager instance exists"""
    assert webhook_manager is not None
    assert isinstance(webhook_manager, WebhookManager)
