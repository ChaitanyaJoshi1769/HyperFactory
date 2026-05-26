"""Webhook service for managing webhooks and deliveries"""

import uuid
import secrets
import requests
import logging
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.webhook import Webhook, WebhookDelivery, WebhookLog, WebhookEventType, WebhookStatus
from app.schemas.webhook import WebhookCreate, WebhookUpdate

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for webhook management"""

    @staticmethod
    def create_webhook(
        db: Session,
        user_id: str,
        webhook_data: WebhookCreate
    ) -> tuple[Webhook, str]:
        """Create a new webhook and return the secret"""
        secret = secrets.token_urlsafe(32)

        db_webhook = Webhook(
            id=uuid.uuid4(),
            user_id=user_id,
            url=webhook_data.url,
            secret=secret,
            status=WebhookStatus.ACTIVE.value,
            events=webhook_data.events,
            description=webhook_data.description,
            max_retries=webhook_data.max_retries,
            retry_delay_seconds=webhook_data.retry_delay_seconds,
            timeout_seconds=webhook_data.timeout_seconds,
        )

        db.add(db_webhook)
        db.commit()
        db.refresh(db_webhook)

        logger.info(f"Created webhook {db_webhook.id} for user {user_id}")
        return db_webhook, secret

    @staticmethod
    def get_webhook(db: Session, webhook_id: str, user_id: str) -> Optional[Webhook]:
        """Get a webhook by ID (user-scoped)"""
        return db.query(Webhook).filter(
            and_(
                Webhook.id == webhook_id,
                Webhook.user_id == user_id,
                Webhook.deleted_at.is_(None)
            )
        ).first()

    @staticmethod
    def list_webhooks(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> tuple[List[Webhook], int]:
        """List webhooks for a user"""
        query = db.query(Webhook).filter(
            and_(
                Webhook.user_id == user_id,
                Webhook.deleted_at.is_(None)
            )
        )

        if status:
            query = query.filter(Webhook.status == status)

        total = query.count()
        webhooks = query.offset(skip).limit(limit).all()

        return webhooks, total

    @staticmethod
    def update_webhook(
        db: Session,
        webhook_id: str,
        user_id: str,
        webhook_data: WebhookUpdate
    ) -> Optional[Webhook]:
        """Update a webhook"""
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        if not webhook:
            return None

        update_data = webhook_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(webhook, key, value)

        webhook.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(webhook)

        logger.info(f"Updated webhook {webhook_id}")
        return webhook

    @staticmethod
    def delete_webhook(db: Session, webhook_id: str, user_id: str) -> bool:
        """Soft delete a webhook"""
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        if not webhook:
            return False

        webhook.deleted_at = datetime.utcnow()
        db.commit()

        logger.info(f"Deleted webhook {webhook_id}")
        return True

    @staticmethod
    def rotate_secret(db: Session, webhook_id: str, user_id: str) -> Optional[str]:
        """Generate a new secret for a webhook"""
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        if not webhook:
            return None

        new_secret = secrets.token_urlsafe(32)
        webhook.secret = new_secret
        webhook.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Rotated secret for webhook {webhook_id}")
        return new_secret

    @staticmethod
    def disable_webhook(db: Session, webhook_id: str) -> bool:
        """Disable a webhook (called when max retries exceeded)"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook:
            return False

        webhook.status = WebhookStatus.DISABLED.value
        webhook.updated_at = datetime.utcnow()
        db.commit()

        logger.warning(f"Disabled webhook {webhook_id} due to repeated failures")
        return True

    @staticmethod
    def queue_delivery(
        db: Session,
        webhook_id: str,
        event_type: str,
        payload: dict
    ) -> Optional[WebhookDelivery]:
        """Queue a webhook delivery"""
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        if not webhook or webhook.status != WebhookStatus.ACTIVE.value:
            return None

        # Check if webhook subscribes to this event
        if event_type not in webhook.events and "*" not in webhook.events:
            return None

        delivery_id = secrets.token_hex(32)

        db_delivery = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=webhook_id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
            status="pending",
            attempt_number=1,
            next_retry_at=datetime.utcnow(),
        )

        db.add(db_delivery)
        db.commit()
        db.refresh(db_delivery)

        logger.info(f"Queued delivery {delivery_id} for webhook {webhook_id}")
        return db_delivery

    @staticmethod
    def get_pending_deliveries(db: Session, limit: int = 100) -> List[WebhookDelivery]:
        """Get pending webhook deliveries"""
        return db.query(WebhookDelivery).filter(
            and_(
                WebhookDelivery.status == "pending",
                or_(
                    WebhookDelivery.next_retry_at.is_(None),
                    WebhookDelivery.next_retry_at <= datetime.utcnow()
                )
            )
        ).limit(limit).all()

    @staticmethod
    def deliver_webhook(
        db: Session,
        delivery_id: str,
        webhook: Webhook
    ) -> tuple[bool, int, int]:
        """Attempt to deliver a webhook"""
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.delivery_id == delivery_id
        ).first()

        if not delivery:
            return False, 0, 0

        # Prepare the signature
        timestamp = str(int(datetime.utcnow().timestamp()))
        signature = WebhookService._create_signature(
            webhook.secret,
            delivery_id,
            timestamp,
            json.dumps(delivery.payload)
        )

        headers = {
            "X-HyperFactory-Signature": signature,
            "X-HyperFactory-Timestamp": timestamp,
            "X-HyperFactory-Delivery-ID": delivery_id,
            "Content-Type": "application/json",
        }

        try:
            start_time = datetime.utcnow()
            response = requests.post(
                webhook.url,
                json=delivery.payload,
                headers=headers,
                timeout=webhook.timeout_seconds
            )
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            delivery.last_attempted_at = datetime.utcnow()
            delivery.response_time_ms = response_time_ms
            delivery.http_status_code = response.status_code

            if 200 <= response.status_code < 300:
                # Success
                delivery.status = "success"
                delivery.completed_at = datetime.utcnow()
                webhook.successful_deliveries += 1
                webhook.last_delivery_at = datetime.utcnow()
                webhook.last_failure_at = None
                webhook.last_failure_reason = None

                logger.info(f"Webhook {webhook.id} delivered successfully ({delivery_id})")
                success = True

            else:
                # Retryable error
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                success = False

        except requests.Timeout:
            delivery.status = "timeout"
            delivery.error_message = "Request timeout"
            success = False

        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)[:200]
            success = False

        # Handle retries
        if not success:
            if delivery.attempt_number < webhook.max_retries:
                # Schedule next retry with exponential backoff
                retry_delay = webhook.retry_delay_seconds * (2 ** (delivery.attempt_number - 1))
                delivery.status = "pending"
                delivery.attempt_number += 1
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                webhook.failed_deliveries += 1
                webhook.last_failure_at = datetime.utcnow()
                webhook.last_failure_reason = delivery.error_message

                logger.warning(f"Webhook {webhook.id} retry {delivery.attempt_number} scheduled")

            else:
                # Max retries exceeded
                delivery.status = "failed"
                delivery.completed_at = datetime.utcnow()
                webhook.failed_deliveries += 1
                webhook.last_failure_at = datetime.utcnow()
                webhook.last_failure_reason = delivery.error_message

                # Disable the webhook
                WebhookService.disable_webhook(db, webhook.id)

                logger.error(f"Webhook {webhook.id} disabled after max retries")

        webhook.total_deliveries += 1
        webhook.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(delivery)
        db.refresh(webhook)

        return success, delivery.response_time_ms or 0, delivery.http_status_code or 0

    @staticmethod
    def get_deliveries(
        db: Session,
        webhook_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> tuple[List[WebhookDelivery], int]:
        """Get delivery history for a webhook"""
        # Verify webhook ownership
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        if not webhook:
            return [], 0

        query = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook_id
        )

        if status:
            query = query.filter(WebhookDelivery.status == status)

        total = query.count()
        deliveries = query.order_by(WebhookDelivery.created_at.desc()).offset(skip).limit(limit).all()

        return deliveries, total

    @staticmethod
    def _create_signature(secret: str, delivery_id: str, timestamp: str, body: str) -> str:
        """Create HMAC signature for webhook"""
        message = f"{delivery_id}.{timestamp}.{body}".encode()
        signature = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @staticmethod
    def verify_webhook_signature(
        secret: str,
        delivery_id: str,
        timestamp: str,
        body: str,
        signature: str
    ) -> bool:
        """Verify webhook signature"""
        expected_signature = WebhookService._create_signature(secret, delivery_id, timestamp, body)
        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    def publish_event(
        db: Session,
        user_id: str,
        event_type: str,
        event_data: dict
    ) -> List[WebhookDelivery]:
        """Publish an event to all subscribed webhooks"""
        webhooks = db.query(Webhook).filter(
            and_(
                Webhook.user_id == user_id,
                Webhook.status == WebhookStatus.ACTIVE.value,
                Webhook.deleted_at.is_(None)
            )
        ).all()

        deliveries = []
        payload = {
            "event": event_type,
            "created_at": datetime.utcnow().isoformat(),
            "data": event_data,
            "version": "1.0"
        }

        for webhook in webhooks:
            delivery = WebhookService.queue_delivery(
                db,
                str(webhook.id),
                event_type,
                payload
            )
            if delivery:
                deliveries.append(delivery)

        return deliveries
