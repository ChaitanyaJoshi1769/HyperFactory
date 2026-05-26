"""Tests for webhook functionality"""

import pytest
import json
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookDelivery, WebhookEventType, WebhookStatus
from app.models.user import User
from app.schemas.webhook import WebhookCreate, WebhookUpdate
from app.services.webhook_service import WebhookService


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        id=uuid4(),
        username="test_webhook_user",
        email="webhook@test.com",
        hashed_password="hashed",
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def webhook_data():
    """Sample webhook creation data"""
    return WebhookCreate(
        url="https://example.com/webhooks",
        events=["factory.created", "job.completed"],
        description="Test webhook",
        max_retries=5,
        retry_delay_seconds=60,
        timeout_seconds=30
    )


class TestWebhookCreation:
    """Test webhook creation"""

    def test_create_webhook(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test creating a webhook"""
        webhook, secret = WebhookService.create_webhook(
            db,
            str(test_user.id),
            webhook_data
        )

        assert webhook.id is not None
        assert webhook.user_id == test_user.id
        assert webhook.url == webhook_data.url
        assert webhook.events == webhook_data.events
        assert webhook.status == WebhookStatus.ACTIVE.value
        assert secret is not None
        assert len(secret) > 0

    def test_webhook_secret_is_unique(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test that each webhook gets a unique secret"""
        _, secret1 = WebhookService.create_webhook(db, str(test_user.id), webhook_data)
        _, secret2 = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        assert secret1 != secret2


class TestWebhookRetrieval:
    """Test webhook retrieval"""

    def test_get_webhook(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test retrieving a webhook"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        retrieved = WebhookService.get_webhook(db, str(webhook.id), str(test_user.id))

        assert retrieved is not None
        assert retrieved.id == webhook.id
        assert retrieved.url == webhook.url

    def test_get_webhook_wrong_user(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test that users can't access other users' webhooks"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        other_user_id = str(uuid4())
        retrieved = WebhookService.get_webhook(db, str(webhook.id), other_user_id)

        assert retrieved is None

    def test_list_webhooks(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test listing webhooks"""
        for i in range(3):
            WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        webhooks, total = WebhookService.list_webhooks(db, str(test_user.id))

        assert len(webhooks) == 3
        assert total == 3

    def test_list_webhooks_with_pagination(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test webhook pagination"""
        for i in range(5):
            WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        page1, _ = WebhookService.list_webhooks(db, str(test_user.id), skip=0, limit=2)
        page2, _ = WebhookService.list_webhooks(db, str(test_user.id), skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestWebhookUpdate:
    """Test webhook updates"""

    def test_update_webhook(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test updating a webhook"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        update_data = WebhookUpdate(
            url="https://updated.example.com/webhooks",
            events=["factory.deleted"]
        )

        updated = WebhookService.update_webhook(db, str(webhook.id), str(test_user.id), update_data)

        assert updated.url == "https://updated.example.com/webhooks"
        assert updated.events == ["factory.deleted"]

    def test_rotate_secret(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test secret rotation"""
        webhook, original_secret = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        new_secret = WebhookService.rotate_secret(db, str(webhook.id), str(test_user.id))

        assert new_secret != original_secret
        assert new_secret is not None


class TestWebhookDeletion:
    """Test webhook deletion"""

    def test_delete_webhook(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test soft delete of webhook"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        success = WebhookService.delete_webhook(db, str(webhook.id), str(test_user.id))

        assert success is True

        # Webhook should not be retrievable after deletion
        retrieved = WebhookService.get_webhook(db, str(webhook.id), str(test_user.id))
        assert retrieved is None


class TestWebhookDelivery:
    """Test webhook delivery queuing and processing"""

    def test_queue_delivery(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test queuing a webhook delivery"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        payload = {
            "factory_id": str(uuid4()),
            "name": "Test Factory"
        }

        delivery = WebhookService.queue_delivery(
            db,
            str(webhook.id),
            "factory.created",
            payload
        )

        assert delivery is not None
        assert delivery.webhook_id == webhook.id
        assert delivery.event_type == "factory.created"
        assert delivery.status == "pending"
        assert delivery.attempt_number == 1

    def test_queue_delivery_filters_by_event(self, db: Session, test_user: User):
        """Test that webhooks only receive subscribed events"""
        webhook_data = WebhookCreate(
            url="https://example.com/webhooks",
            events=["factory.created"],  # Only subscribed to this event
            description="Test"
        )
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        # Try to deliver unsubscribed event
        delivery = WebhookService.queue_delivery(
            db,
            str(webhook.id),
            "factory.deleted",  # Not subscribed
            {"test": "data"}
        )

        assert delivery is None

    def test_queue_delivery_disabled_webhook(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test that deliveries can't be queued for disabled webhooks"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        # Disable the webhook
        WebhookService.disable_webhook(db, str(webhook.id))

        # Try to queue delivery
        delivery = WebhookService.queue_delivery(
            db,
            str(webhook.id),
            "factory.created",
            {"test": "data"}
        )

        assert delivery is None

    def test_get_pending_deliveries(self, db: Session, test_user: User, webhook_data: WebhookCreate):
        """Test retrieving pending deliveries"""
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        # Queue multiple deliveries
        for i in range(3):
            WebhookService.queue_delivery(
                db,
                str(webhook.id),
                "factory.created",
                {"index": i}
            )

        pending = WebhookService.get_pending_deliveries(db)

        assert len(pending) >= 3
        assert all(d.status == "pending" for d in pending[:3])


class TestWebhookSignature:
    """Test webhook signature verification"""

    def test_signature_verification(self):
        """Test HMAC signature creation and verification"""
        secret = "test-secret-key"
        delivery_id = "delivery-123"
        timestamp = "1234567890"
        body = '{"test": "data"}'

        signature = WebhookService._create_signature(secret, delivery_id, timestamp, body)

        # Signature should start with sha256=
        assert signature.startswith("sha256=")

        # Same inputs should produce same signature
        same_signature = WebhookService._create_signature(secret, delivery_id, timestamp, body)
        assert signature == same_signature

        # Different inputs should produce different signature
        different_signature = WebhookService._create_signature(
            secret, delivery_id, timestamp, '{"test": "data2"}'
        )
        assert signature != different_signature

    def test_verify_webhook_signature(self):
        """Test signature verification"""
        secret = "test-secret-key"
        delivery_id = "delivery-123"
        timestamp = "1234567890"
        body = '{"test": "data"}'

        signature = WebhookService._create_signature(secret, delivery_id, timestamp, body)

        # Valid signature should verify
        assert WebhookService.verify_webhook_signature(
            secret, delivery_id, timestamp, body, signature
        ) is True

        # Invalid signature should not verify
        assert WebhookService.verify_webhook_signature(
            secret, delivery_id, timestamp, body, "sha256=invalid"
        ) is False

        # Different secret should not verify
        assert WebhookService.verify_webhook_signature(
            "wrong-secret", delivery_id, timestamp, body, signature
        ) is False


class TestPublishEvent:
    """Test event publishing to webhooks"""

    def test_publish_event_to_subscribed_webhooks(self, db: Session, test_user: User):
        """Test that events are published to subscribed webhooks"""
        webhook_data1 = WebhookCreate(
            url="https://example.com/webhook1",
            events=["factory.created"],
            description="Webhook 1"
        )
        webhook_data2 = WebhookCreate(
            url="https://example.com/webhook2",
            events=["factory.created", "job.completed"],
            description="Webhook 2"
        )
        webhook_data3 = WebhookCreate(
            url="https://example.com/webhook3",
            events=["job.completed"],  # Doesn't subscribe to factory.created
            description="Webhook 3"
        )

        webhook1, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data1)
        webhook2, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data2)
        webhook3, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data3)

        # Publish event
        event_data = {"factory_id": str(uuid4()), "name": "New Factory"}
        deliveries = WebhookService.publish_event(
            db,
            str(test_user.id),
            "factory.created",
            event_data
        )

        # Should deliver to webhook1 and webhook2, but not webhook3
        assert len(deliveries) == 2
        delivery_webhook_ids = [d.webhook_id for d in deliveries]
        assert webhook1.id in delivery_webhook_ids
        assert webhook2.id in delivery_webhook_ids
        assert webhook3.id not in delivery_webhook_ids

    def test_publish_event_wildcard_subscription(self, db: Session, test_user: User):
        """Test wildcard event subscription"""
        webhook_data = WebhookCreate(
            url="https://example.com/webhook",
            events=["*"],  # Subscribe to all events
            description="Catch-all webhook"
        )
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        # Publish any event
        deliveries = WebhookService.publish_event(
            db,
            str(test_user.id),
            "factory.created",
            {"test": "data"}
        )

        assert len(deliveries) == 1
        assert deliveries[0].webhook_id == webhook.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
