"""Webhook Management - Event-driven integration with delivery and retry logic"""

import secrets
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict


# Configuration
WEBHOOK_SIGNATURE_HEADER = "X-HyperFactory-Signature"
WEBHOOK_TIMESTAMP_HEADER = "X-HyperFactory-Timestamp"
WEBHOOK_DELIVERY_ID_HEADER = "X-HyperFactory-Delivery-ID"
WEBHOOK_MAX_RETRIES = 5
WEBHOOK_INITIAL_RETRY_DELAY_SECONDS = 60
WEBHOOK_MAX_RETRY_DELAY_SECONDS = 3600  # 1 hour
WEBHOOK_REQUEST_TIMEOUT_SECONDS = 30
WEBHOOK_SIGNATURE_TTL_SECONDS = 300  # 5 minutes


class WebhookEvent(str, Enum):
    """Supported webhook events"""
    # Factory events
    FACTORY_CREATED = "factory.created"
    FACTORY_UPDATED = "factory.updated"
    FACTORY_DELETED = "factory.deleted"

    # Machine events
    MACHINE_CREATED = "machine.created"
    MACHINE_UPDATED = "machine.updated"
    MACHINE_DELETED = "machine.deleted"

    # Production job events
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"

    # CAD analysis events
    CAD_ANALYSIS_COMPLETED = "cad.analysis_completed"
    CAD_ANALYSIS_FAILED = "cad.analysis_failed"

    # User/account events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"


class WebhookEventStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"  # Waiting to be delivered
    DELIVERED = "delivered"  # Successfully delivered
    FAILED = "failed"  # Failed after max retries
    DISABLED = "disabled"  # Webhook disabled


class WebhookDeliveryStatus(str, Enum):
    """Individual delivery attempt status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class WebhookPayload:
    """Webhook event payload"""
    event: str  # Event type
    created_at: str  # ISO 8601 timestamp
    data: Dict  # Event-specific data
    version: str = "1.0"  # Webhook API version

    def to_json(self) -> str:
        """Convert payload to JSON string"""
        return json.dumps(asdict(self))


@dataclass
class WebhookDeliveryAttempt:
    """Record of a webhook delivery attempt"""
    id: str  # Unique delivery attempt ID
    webhook_id: str  # Webhook ID
    attempt_number: int
    status: WebhookDeliveryStatus
    http_status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def __init__(
        self,
        webhook_id: str,
        attempt_number: int,
        status: WebhookDeliveryStatus,
    ):
        self.id = secrets.token_hex(16)
        self.webhook_id = webhook_id
        self.attempt_number = attempt_number
        self.status = status
        self.timestamp = datetime.utcnow().isoformat()


class Webhook:
    """Webhook subscription"""

    def __init__(
        self,
        webhook_id: str,
        user_id: str,
        url: str,
        events: List[WebhookEvent],
        secret: str,
        is_active: bool = True,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize webhook.

        Args:
            webhook_id: Unique webhook identifier
            user_id: User who created the webhook
            url: Webhook delivery URL
            events: List of events to subscribe to
            secret: Secret key for signing webhook payloads
            is_active: Whether webhook is active
            custom_headers: Custom HTTP headers to include in requests
        """
        self.webhook_id = webhook_id
        self.user_id = user_id
        self.url = url
        self.events = events
        self.secret = secret
        self.is_active = is_active
        self.custom_headers = custom_headers or {}
        self.created_at = datetime.utcnow()
        self.last_triggered_at: Optional[datetime] = None
        self.failure_count = 0
        self.consecutive_failures = 0
        self.delivery_attempts: List[WebhookDeliveryAttempt] = []

    def matches_event(self, event: WebhookEvent) -> bool:
        """Check if webhook subscribes to this event"""
        return event in self.events

    def disable_after_failures(self, threshold: int = 10) -> bool:
        """Disable webhook if too many consecutive failures"""
        if self.consecutive_failures >= threshold:
            self.is_active = False
            logging.warning(
                f"Webhook {self.webhook_id} disabled after {self.consecutive_failures} consecutive failures"
            )
            return True
        return False

    def reset_failure_count(self):
        """Reset failure count on successful delivery"""
        self.consecutive_failures = 0

    def increment_failure_count(self):
        """Increment failure count"""
        self.failure_count += 1
        self.consecutive_failures += 1


class WebhookManager:
    """Manages webhook subscriptions and deliveries"""

    def __init__(self):
        """Initialize webhook manager"""
        self.logger = logging.getLogger("webhook_manager")

        # In-memory storage (use database in production)
        self._webhooks: Dict[str, Webhook] = {}
        self._events_queue: List[Tuple[WebhookEvent, Dict]] = []
        self._delivery_hooks: List[Callable] = []

    @staticmethod
    def generate_webhook_id() -> str:
        """Generate unique webhook ID"""
        return secrets.token_hex(16)

    @staticmethod
    def generate_secret() -> str:
        """Generate webhook secret"""
        return secrets.token_hex(32)

    def register_delivery_hook(self, hook: Callable) -> None:
        """
        Register a delivery hook (for custom delivery implementation).

        Hook signature: hook(webhook, payload) -> bool
        """
        self._delivery_hooks.append(hook)

    def create_webhook(
        self,
        user_id: str,
        url: str,
        events: List[WebhookEvent],
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, str]:  # (webhook_id, secret)
        """
        Create new webhook subscription.

        Args:
            user_id: User creating the webhook
            url: Delivery URL
            events: Events to subscribe to
            custom_headers: Custom HTTP headers

        Returns:
            Tuple of (webhook_id, secret)
        """
        webhook_id = self.generate_webhook_id()
        secret = self.generate_secret()

        webhook = Webhook(
            webhook_id=webhook_id,
            user_id=user_id,
            url=url,
            events=events,
            secret=secret,
            custom_headers=custom_headers,
        )

        self._webhooks[webhook_id] = webhook

        self.logger.info(
            f"Webhook created",
            extra={
                "webhook_id": webhook_id,
                "user_id": user_id,
                "url": url,
                "events": [e.value for e in events],
            }
        )

        return webhook_id, secret

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID"""
        return self._webhooks.get(webhook_id)

    def get_user_webhooks(self, user_id: str) -> List[Webhook]:
        """Get all webhooks for a user"""
        return [w for w in self._webhooks.values() if w.user_id == user_id]

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook"""
        if webhook_id in self._webhooks:
            webhook = self._webhooks[webhook_id]
            del self._webhooks[webhook_id]

            self.logger.info(
                f"Webhook deleted",
                extra={"webhook_id": webhook_id, "user_id": webhook.user_id}
            )
            return True

        return False

    def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[WebhookEvent]] = None,
        is_active: Optional[bool] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Update webhook configuration"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False

        if url:
            webhook.url = url
        if events:
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active
        if custom_headers is not None:
            webhook.custom_headers = custom_headers

        return True

    def enqueue_event(self, event: WebhookEvent, data: Dict) -> None:
        """
        Enqueue event for webhook delivery.

        Args:
            event: Event type
            data: Event-specific data
        """
        self._events_queue.append((event, data))

        self.logger.debug(
            f"Event enqueued",
            extra={"event": event.value, "queue_size": len(self._events_queue)}
        )

    def process_events(self) -> int:
        """
        Process all queued events and deliver to matching webhooks.

        Returns:
            Number of events processed
        """
        processed = 0

        while self._events_queue:
            event, data = self._events_queue.pop(0)

            # Find matching webhooks
            matching_webhooks = [
                w for w in self._webhooks.values()
                if w.is_active and w.matches_event(event)
            ]

            # Event is processed even if no webhooks match
            processed += 1

            if not matching_webhooks:
                continue

            # Create payload
            payload = WebhookPayload(
                event=event.value,
                created_at=datetime.utcnow().isoformat(),
                data=data,
            )

            # Deliver to each matching webhook
            for webhook in matching_webhooks:
                self._enqueue_delivery(webhook, payload)

        return processed

    def _enqueue_delivery(self, webhook: Webhook, payload: WebhookPayload) -> None:
        """Enqueue webhook delivery"""
        self.logger.debug(
            f"Webhook delivery enqueued",
            extra={"webhook_id": webhook.webhook_id, "event": payload.event}
        )

        # Call delivery hooks
        for hook in self._delivery_hooks:
            try:
                hook(webhook, payload)
            except Exception as e:
                self.logger.error(
                    f"Delivery hook failed: {str(e)}",
                    extra={"webhook_id": webhook.webhook_id}
                )

    def sign_payload(self, webhook_id: str, payload_json: str) -> Optional[str]:
        """
        Sign webhook payload using HMAC-SHA256.

        Args:
            webhook_id: Webhook ID
            payload_json: JSON payload string

        Returns:
            Signature value (format: "sha256=hex_signature")
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None

        import hmac
        import hashlib

        signature_hex = hmac.new(
            webhook.secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature_hex}"

    def verify_webhook_signature(
        self,
        webhook_id: str,
        signature: str,
        payload_json: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify webhook payload signature.

        Args:
            webhook_id: Webhook ID
            signature: Signature header value
            payload_json: JSON payload string

        Returns:
            Tuple of (is_valid, error_message)
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False, "webhook_not_found"

        expected_signature = self.sign_payload(webhook_id, payload_json)
        if not expected_signature:
            return False, "signature_generation_failed"

        import hmac

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            self.logger.warning(
                f"Webhook signature verification failed",
                extra={
                    "webhook_id": webhook_id,
                    "expected": expected_signature[:20],
                    "received": signature[:20],
                }
            )

        return is_valid, None if is_valid else "invalid_signature"

    def record_delivery_attempt(
        self,
        webhook_id: str,
        attempt_number: int,
        status: WebhookDeliveryStatus,
        http_status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> str:  # delivery_attempt_id
        """
        Record webhook delivery attempt.

        Args:
            webhook_id: Webhook ID
            attempt_number: Attempt number
            status: Delivery status
            http_status_code: HTTP response status code
            response_time_ms: Response time in milliseconds
            error_message: Error message if failed

        Returns:
            Delivery attempt ID
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return ""

        attempt = WebhookDeliveryAttempt(
            webhook_id=webhook_id,
            attempt_number=attempt_number,
            status=status,
        )

        attempt.http_status_code = http_status_code
        attempt.response_time_ms = response_time_ms
        attempt.error_message = error_message

        webhook.delivery_attempts.append(attempt)
        webhook.last_triggered_at = datetime.utcnow()

        if status == WebhookDeliveryStatus.SUCCESS:
            webhook.reset_failure_count()
        else:
            webhook.increment_failure_count()
            webhook.disable_after_failures()

        self.logger.info(
            f"Webhook delivery attempt recorded",
            extra={
                "webhook_id": webhook_id,
                "attempt": attempt_number,
                "status": status.value,
                "http_code": http_status_code,
            }
        )

        return attempt.id

    def get_delivery_history(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> List[WebhookDeliveryAttempt]:
        """Get recent delivery history for webhook"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return []

        return webhook.delivery_attempts[-limit:]

    def get_webhook_stats(self, webhook_id: str) -> Dict:
        """Get webhook statistics"""
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return {}

        total_attempts = len(webhook.delivery_attempts)
        successful = sum(
            1 for a in webhook.delivery_attempts
            if a.status == WebhookDeliveryStatus.SUCCESS
        )
        failed = sum(
            1 for a in webhook.delivery_attempts
            if a.status == WebhookDeliveryStatus.FAILED
        )

        avg_response_time = None
        if webhook.delivery_attempts:
            response_times = [
                a.response_time_ms for a in webhook.delivery_attempts
                if a.response_time_ms
            ]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        return {
            "webhook_id": webhook_id,
            "url": webhook.url,
            "is_active": webhook.is_active,
            "created_at": webhook.created_at.isoformat(),
            "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
            "total_attempts": total_attempts,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_attempts if total_attempts > 0 else 0,
            "consecutive_failures": webhook.consecutive_failures,
            "avg_response_time_ms": avg_response_time,
        }


# Global webhook manager instance
webhook_manager = WebhookManager()
