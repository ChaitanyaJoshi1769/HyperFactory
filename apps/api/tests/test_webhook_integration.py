"""End-to-end integration tests for webhook event publishing"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookDelivery, WebhookStatus
from app.models.user import User
from app.models.factory import FactoryConfig, Machine, ProductionJob
from app.schemas.webhook import WebhookCreate
from app.schemas.factory import FactoryConfigCreate, MachineCreate, ProductionJobCreate
from app.services.webhook_service import WebhookService
from app.event_publisher import EventPublisher


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
def webhook_subscription(db: Session, test_user: User):
    """Create a webhook subscription to all factory events"""
    webhook_data = WebhookCreate(
        url="https://example.com/webhooks",
        events=["factory.*", "job.*"],  # Subscribe to factory and job events
        description="Test webhook for integration"
    )
    webhook, secret = WebhookService.create_webhook(
        db,
        str(test_user.id),
        webhook_data
    )
    return webhook, secret


class TestFactoryEventPublishing:
    """Test webhook event publishing for factory operations"""

    def test_factory_creation_publishes_event(self, db: Session, webhook_subscription):
        """Test that factory.created event is published when factory is created"""
        webhook, _ = webhook_subscription

        # Create a factory
        factory_data = FactoryConfigCreate(
            name="Test Factory",
            location="Test Location",
            status="operational"
        )
        factory = FactoryConfig(**factory_data.dict())
        db.add(factory)
        db.commit()
        db.refresh(factory)

        # Publish event manually (in real API, this happens in router)
        EventPublisher.factory_created(
            db=db,
            user_id=str(webhook.user_id),
            factory_id=str(factory.id),
            name=factory.name,
            location=factory.location,
            status=factory.status
        )

        # Verify webhook delivery was queued
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id,
            WebhookDelivery.event_type == "factory.created"
        ).first()

        assert delivery is not None
        assert delivery.status == "pending"
        assert delivery.payload["data"]["factory_id"] == str(factory.id)
        assert delivery.payload["data"]["name"] == "Test Factory"
        assert delivery.payload["event"] == "factory.created"

    def test_factory_update_publishes_event(self, db: Session, webhook_subscription):
        """Test that factory.updated event is published when factory is updated"""
        webhook, _ = webhook_subscription

        # Create and update a factory
        factory = FactoryConfig(
            name="Original Factory",
            location="Original Location",
            status="operational"
        )
        db.add(factory)
        db.commit()
        db.refresh(factory)

        # Update factory
        factory.name = "Updated Factory"
        db.commit()

        # Publish event
        EventPublisher.factory_updated(
            db=db,
            user_id=str(webhook.user_id),
            factory_id=str(factory.id),
            name=factory.name,
            changes={"name": {"old": "Original Factory", "new": "Updated Factory"}}
        )

        # Verify delivery
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id,
            WebhookDelivery.event_type == "factory.updated"
        ).first()

        assert delivery is not None
        assert delivery.payload["data"]["changes"]["name"]["new"] == "Updated Factory"

    def test_factory_deletion_publishes_event(self, db: Session, webhook_subscription):
        """Test that factory.deleted event is published when factory is deleted"""
        webhook, _ = webhook_subscription

        # Create and delete a factory
        factory = FactoryConfig(
            name="Temporary Factory",
            location="Temp Location"
        )
        db.add(factory)
        db.commit()
        db.refresh(factory)

        factory_id = factory.id
        factory_name = factory.name

        db.delete(factory)
        db.commit()

        # Publish event
        EventPublisher.factory_deleted(
            db=db,
            user_id=str(webhook.user_id),
            factory_id=str(factory_id),
            name=factory_name
        )

        # Verify delivery
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id,
            WebhookDelivery.event_type == "factory.deleted"
        ).first()

        assert delivery is not None
        assert delivery.payload["data"]["name"] == factory_name


class TestJobEventPublishing:
    """Test webhook event publishing for production jobs"""

    def test_job_creation_publishes_event(self, db: Session, webhook_subscription):
        """Test that job.created event is published when job is created"""
        webhook, _ = webhook_subscription

        # Create job
        job = ProductionJob(
            part_id=uuid4(),
            machine_id=uuid4(),
            quantity=10,
            status="queued",
            priority="high"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Publish event
        EventPublisher.job_created(
            db=db,
            user_id=str(webhook.user_id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            machine_id=str(job.machine_id),
            quantity=job.quantity
        )

        # Verify delivery
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id,
            WebhookDelivery.event_type == "job.created"
        ).first()

        assert delivery is not None
        assert delivery.payload["data"]["quantity"] == 10

    def test_job_lifecycle_publishes_events(self, db: Session, webhook_subscription):
        """Test that job lifecycle events are published"""
        webhook, _ = webhook_subscription

        # Create job
        job = ProductionJob(
            part_id=uuid4(),
            machine_id=uuid4(),
            quantity=5,
            status="queued"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Publish job.created
        EventPublisher.job_created(
            db=db,
            user_id=str(webhook.user_id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            machine_id=str(job.machine_id),
            quantity=5
        )

        # Simulate job starting
        job.status = "in_progress"
        job.start_time = datetime.utcnow()
        db.commit()

        EventPublisher.job_started(
            db=db,
            user_id=str(webhook.user_id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            machine_id=str(job.machine_id),
            estimated_duration_minutes=120
        )

        # Simulate job completion
        job.status = "completed"
        job.completion_time = datetime.utcnow()
        job.actual_duration_minutes = 115
        job.actual_cost = 250.50
        job.quality_checks_passed = 5
        job.quality_checks_failed = 0
        db.commit()

        EventPublisher.job_completed(
            db=db,
            user_id=str(webhook.user_id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            quantity=5,
            actual_duration_minutes=115,
            actual_cost=250.50,
            quality_passed=5,
            quality_failed=0
        )

        # Verify all three deliveries were created
        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id
        ).all()

        assert len(deliveries) >= 3

        event_types = [d.event_type for d in deliveries]
        assert "job.created" in event_types
        assert "job.started" in event_types
        assert "job.completed" in event_types

    def test_job_failure_publishes_event(self, db: Session, webhook_subscription):
        """Test that job.failed event is published on job failure"""
        webhook, _ = webhook_subscription

        job = ProductionJob(
            part_id=uuid4(),
            machine_id=uuid4(),
            quantity=1,
            status="queued"
        )
        db.add(job)
        db.commit()

        # Publish job failure
        EventPublisher.job_failed(
            db=db,
            user_id=str(webhook.user_id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            reason="Machine malfunction",
            error_message="Spindle bearing failure detected"
        )

        # Verify delivery
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id,
            WebhookDelivery.event_type == "job.failed"
        ).first()

        assert delivery is not None
        assert delivery.payload["data"]["reason"] == "Machine malfunction"


class TestMultipleWebhookSubscriptions:
    """Test that multiple webhooks receive the same events"""

    def test_multiple_webhooks_receive_factory_event(self, db: Session, test_user: User):
        """Test that multiple webhook subscriptions both receive events"""
        # Create two webhooks
        webhook_data1 = WebhookCreate(
            url="https://example1.com/webhooks",
            events=["factory.*"],
            description="Webhook 1"
        )
        webhook_data2 = WebhookCreate(
            url="https://example2.com/webhooks",
            events=["factory.created"],  # Only factory.created
            description="Webhook 2"
        )

        webhook1, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data1)
        webhook2, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data2)

        # Create factory
        factory = FactoryConfig(name="Multi-Webhook Factory")
        db.add(factory)
        db.commit()

        # Publish event
        EventPublisher.factory_created(
            db=db,
            user_id=str(test_user.id),
            factory_id=str(factory.id),
            name=factory.name,
            location=""
        )

        # Both webhooks should have pending deliveries
        delivery1 = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook1.id,
            WebhookDelivery.event_type == "factory.created"
        ).first()

        delivery2 = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook2.id,
            WebhookDelivery.event_type == "factory.created"
        ).first()

        assert delivery1 is not None
        assert delivery2 is not None
        assert delivery1.status == "pending"
        assert delivery2.status == "pending"


class TestEventFiltering:
    """Test that event subscriptions filter correctly"""

    def test_selective_event_subscription(self, db: Session, test_user: User):
        """Test that webhooks only receive subscribed events"""
        # Create webhook that only subscribes to factory events
        webhook_data = WebhookCreate(
            url="https://example.com/webhooks",
            events=["factory.created", "factory.updated"],  # No job events
            description="Factory-only webhook"
        )
        webhook, _ = WebhookService.create_webhook(db, str(test_user.id), webhook_data)

        # Publish factory event
        factory = FactoryConfig(name="Test Factory")
        db.add(factory)
        db.commit()

        EventPublisher.factory_created(
            db=db,
            user_id=str(test_user.id),
            factory_id=str(factory.id),
            name=factory.name,
            location=""
        )

        # Publish job event
        job = ProductionJob(
            part_id=uuid4(),
            machine_id=uuid4(),
            quantity=1,
            status="queued"
        )
        db.add(job)
        db.commit()

        EventPublisher.job_created(
            db=db,
            user_id=str(test_user.id),
            job_id=str(job.id),
            part_id=str(job.part_id),
            machine_id=str(job.machine_id),
            quantity=1
        )

        # Webhook should only have factory event, not job event
        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook.id
        ).all()

        event_types = [d.event_type for d in deliveries]
        assert "factory.created" in event_types
        assert "job.created" not in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
