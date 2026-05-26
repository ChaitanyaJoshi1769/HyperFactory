"""Webhooks router for managing webhook subscriptions and deliveries"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import json

from app.db import get_db
from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import (
    WebhookCreate,
    WebhookRead,
    WebhookUpdate,
    WebhookDeliveryRead,
    WebhookDeliveryListRead,
    WebhookTestRequest,
    WebhookTestResponse,
    WebhookSecret,
)
from app.services.webhook_service import WebhookService

# Mock auth - replace with real auth dependency
def get_current_user_id():
    """Get current user ID from token"""
    # This should be replaced with real authentication
    return "mock-user-id"

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ============================================================================
# Webhook Management Endpoints
# ============================================================================

@router.post("", response_model=WebhookSecret, status_code=201)
def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new webhook subscription.

    The secret returned here should be stored securely and used to verify webhook signatures.
    You won't be able to retrieve this secret again, so save it immediately.
    """
    webhook, secret = WebhookService.create_webhook(db, user_id, webhook_data)

    return WebhookSecret(
        webhook_id=webhook.id,
        secret=secret,
    )


@router.get("", response_model=List[WebhookRead])
def list_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str = Query(None, description="Filter by webhook status (active/disabled/failed)"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """List all webhooks for the current user"""
    webhooks, _ = WebhookService.list_webhooks(db, user_id, skip, limit, status)
    return webhooks


@router.get("/{webhook_id}", response_model=WebhookRead)
def get_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get webhook details"""
    webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookRead)
def update_webhook(
    webhook_id: UUID,
    webhook_data: WebhookUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Update webhook configuration"""
    webhook = WebhookService.update_webhook(db, str(webhook_id), user_id, webhook_data)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a webhook"""
    success = WebhookService.delete_webhook(db, str(webhook_id), user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")


# ============================================================================
# Secret Management Endpoints
# ============================================================================

@router.post("/{webhook_id}/rotate-secret", response_model=WebhookSecret)
def rotate_secret(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Rotate webhook secret.

    Generates a new secret for the webhook. The old secret will no longer work.
    Save the new secret immediately as you won't be able to retrieve it again.
    """
    secret = WebhookService.rotate_secret(db, str(webhook_id), user_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookSecret(
        webhook_id=webhook_id,
        secret=secret,
    )


# ============================================================================
# Delivery History Endpoints
# ============================================================================

@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListRead)
def get_deliveries(
    webhook_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str = Query(None, description="Filter by delivery status (pending/success/failed/timeout)"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get delivery history for a webhook"""
    deliveries, total = WebhookService.get_deliveries(
        db, str(webhook_id), user_id, skip, limit, status
    )
    if not deliveries and skip == 0:  # Check if webhook exists
        webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

    successful = len([d for d in deliveries if d.status == "success"])
    failed = len([d for d in deliveries if d.status == "failed"])
    pending = len([d for d in deliveries if d.status == "pending"])

    return WebhookDeliveryListRead(
        deliveries=deliveries,
        total=total,
        successful=successful,
        failed=failed,
        pending=pending,
    )


@router.get("/{webhook_id}/deliveries/{delivery_id}", response_model=WebhookDeliveryRead)
def get_delivery(
    webhook_id: UUID,
    delivery_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get details about a specific delivery"""
    # Verify webhook ownership
    webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    delivery = db.query(WebhookDelivery).filter(
        WebhookDelivery.delivery_id == delivery_id,
        WebhookDelivery.webhook_id == webhook_id
    ).first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    return delivery


# ============================================================================
# Testing Endpoints
# ============================================================================

@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(
    webhook_id: UUID,
    test_request: WebhookTestRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a test event to a webhook.

    Useful for verifying your webhook URL is working and that you can parse the signature.
    """
    webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Create test payload
    test_payload = test_request.payload or {
        "test": True,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This is a test webhook event"
    }

    # Queue the delivery
    delivery = WebhookService.queue_delivery(
        db,
        str(webhook_id),
        test_request.event_type,
        {
            "event": test_request.event_type,
            "created_at": datetime.utcnow().isoformat(),
            "data": test_payload,
            "version": "1.0"
        }
    )

    if not delivery:
        raise HTTPException(
            status_code=400,
            detail="Failed to queue test delivery. Webhook may be disabled."
        )

    # Attempt immediate delivery
    success, response_time, http_status = WebhookService.deliver_webhook(
        db, delivery.delivery_id, webhook
    )

    return WebhookTestResponse(
        delivery_id=delivery.delivery_id,
        status=delivery.status,
        http_status_code=http_status,
        response_time_ms=response_time,
        success=success,
        message="Test webhook sent" if success else f"Test webhook failed: {delivery.error_message}"
    )


# ============================================================================
# Retry Endpoints
# ============================================================================

@router.post("/{webhook_id}/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryRead)
def retry_delivery(
    webhook_id: UUID,
    delivery_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Manually retry a failed webhook delivery"""
    # Verify webhook ownership
    webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    delivery = db.query(WebhookDelivery).filter(
        WebhookDelivery.delivery_id == delivery_id,
        WebhookDelivery.webhook_id == webhook_id
    ).first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.status == "pending":
        raise HTTPException(status_code=400, detail="Cannot retry a pending delivery")

    # Reset for retry
    from datetime import datetime
    delivery.status = "pending"
    delivery.attempt_number = 1
    delivery.next_retry_at = datetime.utcnow()
    delivery.last_attempted_at = None
    delivery.completed_at = None
    delivery.error_message = None

    db.commit()
    db.refresh(delivery)

    return delivery


# ============================================================================
# Health & Stats Endpoints
# ============================================================================

@router.get("/{webhook_id}/stats", response_model=WebhookRead)
def get_webhook_stats(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get webhook statistics and health"""
    webhook = WebhookService.get_webhook(db, str(webhook_id), user_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


# Import at the end to avoid circular imports
from datetime import datetime
