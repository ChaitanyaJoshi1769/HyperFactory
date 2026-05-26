"""Event publisher for webhook integration with API operations"""

import logging
from typing import Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.webhook_service import WebhookService
from app.models.webhook import WebhookEventType

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events to webhooks when API operations occur"""

    @staticmethod
    def publish(
        db: Session,
        user_id: str,
        event_type: str,
        event_data: dict,
        description: str = None
    ) -> bool:
        """Publish an event to all subscribed webhooks"""
        try:
            deliveries = WebhookService.publish_event(
                db,
                user_id,
                event_type,
                event_data
            )

            if deliveries:
                logger.info(
                    f"Published event {event_type} to {len(deliveries)} webhooks"
                    f"{' - ' + description if description else ''}"
                )
            else:
                logger.debug(f"No active webhooks for event {event_type}")

            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {str(e)}")
            return False

    # =========================================================================
    # Factory Events
    # =========================================================================

    @staticmethod
    def factory_created(
        db: Session,
        user_id: str,
        factory_id: str,
        name: str,
        location: str,
        **kwargs
    ):
        """Publish factory.created event"""
        event_data = {
            "factory_id": factory_id,
            "name": name,
            "location": location,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.FACTORY_CREATED.value, event_data,
            f"Factory '{name}' created"
        )

    @staticmethod
    def factory_updated(
        db: Session,
        user_id: str,
        factory_id: str,
        name: str,
        changes: dict,
        **kwargs
    ):
        """Publish factory.updated event"""
        event_data = {
            "factory_id": factory_id,
            "name": name,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.FACTORY_UPDATED.value, event_data,
            f"Factory '{name}' updated"
        )

    @staticmethod
    def factory_deleted(
        db: Session,
        user_id: str,
        factory_id: str,
        name: str,
        **kwargs
    ):
        """Publish factory.deleted event"""
        event_data = {
            "factory_id": factory_id,
            "name": name,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.FACTORY_DELETED.value, event_data,
            f"Factory '{name}' deleted"
        )

    # =========================================================================
    # Machine Events
    # =========================================================================

    @staticmethod
    def machine_created(
        db: Session,
        user_id: str,
        machine_id: str,
        name: str,
        factory_id: str,
        **kwargs
    ):
        """Publish machine.created event"""
        event_data = {
            "machine_id": machine_id,
            "name": name,
            "factory_id": factory_id,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.MACHINE_CREATED.value, event_data,
            f"Machine '{name}' added to factory"
        )

    @staticmethod
    def machine_updated(
        db: Session,
        user_id: str,
        machine_id: str,
        name: str,
        changes: dict,
        **kwargs
    ):
        """Publish machine.updated event"""
        event_data = {
            "machine_id": machine_id,
            "name": name,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.MACHINE_UPDATED.value, event_data,
            f"Machine '{name}' configuration updated"
        )

    @staticmethod
    def machine_deleted(
        db: Session,
        user_id: str,
        machine_id: str,
        name: str,
        **kwargs
    ):
        """Publish machine.deleted event"""
        event_data = {
            "machine_id": machine_id,
            "name": name,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.MACHINE_DELETED.value, event_data,
            f"Machine '{name}' removed"
        )

    # =========================================================================
    # Production Job Events
    # =========================================================================

    @staticmethod
    def job_created(
        db: Session,
        user_id: str,
        job_id: str,
        part_id: str,
        machine_id: str,
        quantity: int,
        **kwargs
    ):
        """Publish job.created event"""
        event_data = {
            "job_id": job_id,
            "part_id": part_id,
            "machine_id": machine_id,
            "quantity": quantity,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.JOB_CREATED.value, event_data,
            f"Production job created (qty: {quantity})"
        )

    @staticmethod
    def job_started(
        db: Session,
        user_id: str,
        job_id: str,
        part_id: str,
        machine_id: str,
        estimated_duration_minutes: int,
        **kwargs
    ):
        """Publish job.started event"""
        event_data = {
            "job_id": job_id,
            "part_id": part_id,
            "machine_id": machine_id,
            "estimated_duration_minutes": estimated_duration_minutes,
            "started_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.JOB_STARTED.value, event_data,
            f"Production job started (est. {estimated_duration_minutes}min)"
        )

    @staticmethod
    def job_completed(
        db: Session,
        user_id: str,
        job_id: str,
        part_id: str,
        quantity: int,
        actual_duration_minutes: int,
        actual_cost: float,
        quality_passed: int,
        quality_failed: int,
        **kwargs
    ):
        """Publish job.completed event"""
        event_data = {
            "job_id": job_id,
            "part_id": part_id,
            "quantity": quantity,
            "actual_duration_minutes": actual_duration_minutes,
            "actual_cost": actual_cost,
            "quality_checks_passed": quality_passed,
            "quality_checks_failed": quality_failed,
            "completed_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.JOB_COMPLETED.value, event_data,
            f"Production job completed (cost: ${actual_cost:.2f})"
        )

    @staticmethod
    def job_failed(
        db: Session,
        user_id: str,
        job_id: str,
        part_id: str,
        reason: str,
        error_message: str = None,
        **kwargs
    ):
        """Publish job.failed event"""
        event_data = {
            "job_id": job_id,
            "part_id": part_id,
            "reason": reason,
            "error_message": error_message,
            "failed_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.JOB_FAILED.value, event_data,
            f"Production job failed: {reason}"
        )

    # =========================================================================
    # CAD Analysis Events
    # =========================================================================

    @staticmethod
    def cad_analysis_completed(
        db: Session,
        user_id: str,
        analysis_id: str,
        part_id: str,
        dfm_score: float,
        manufacturability_issues: list,
        optimization_recommendations: list,
        **kwargs
    ):
        """Publish cad.analysis_completed event"""
        event_data = {
            "analysis_id": analysis_id,
            "part_id": part_id,
            "dfm_score": dfm_score,
            "manufacturability_issues": manufacturability_issues,
            "optimization_recommendations": optimization_recommendations,
            "completed_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.CAD_ANALYSIS_COMPLETED.value, event_data,
            f"CAD analysis completed (DFM: {dfm_score:.1f}%)"
        )

    @staticmethod
    def cad_analysis_failed(
        db: Session,
        user_id: str,
        analysis_id: str,
        part_id: str,
        error_reason: str,
        error_message: str = None,
        **kwargs
    ):
        """Publish cad.analysis_failed event"""
        event_data = {
            "analysis_id": analysis_id,
            "part_id": part_id,
            "error_reason": error_reason,
            "error_message": error_message,
            "failed_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.CAD_ANALYSIS_FAILED.value, event_data,
            f"CAD analysis failed: {error_reason}"
        )

    # =========================================================================
    # Hardware Part Events
    # =========================================================================

    @staticmethod
    def part_created(
        db: Session,
        user_id: str,
        part_id: str,
        name: str,
        part_type: str,
        **kwargs
    ):
        """Publish part.created event"""
        event_data = {
            "part_id": part_id,
            "name": name,
            "type": part_type,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.PART_CREATED.value, event_data,
            f"Hardware part '{name}' created"
        )

    @staticmethod
    def part_updated(
        db: Session,
        user_id: str,
        part_id: str,
        name: str,
        changes: dict,
        **kwargs
    ):
        """Publish part.updated event"""
        event_data = {
            "part_id": part_id,
            "name": name,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.PART_UPDATED.value, event_data,
            f"Hardware part '{name}' updated"
        )

    @staticmethod
    def part_deleted(
        db: Session,
        user_id: str,
        part_id: str,
        name: str,
        **kwargs
    ):
        """Publish part.deleted event"""
        event_data = {
            "part_id": part_id,
            "name": name,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.PART_DELETED.value, event_data,
            f"Hardware part '{name}' deleted"
        )

    # =========================================================================
    # User/Account Events
    # =========================================================================

    @staticmethod
    def user_created(
        db: Session,
        user_id: str,
        username: str,
        email: str,
        **kwargs
    ):
        """Publish user.created event"""
        event_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.USER_CREATED.value, event_data,
            f"User '{username}' created"
        )

    @staticmethod
    def user_updated(
        db: Session,
        user_id: str,
        username: str,
        changes: dict,
        **kwargs
    ):
        """Publish user.updated event"""
        event_data = {
            "user_id": user_id,
            "username": username,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.USER_UPDATED.value, event_data,
            f"User '{username}' profile updated"
        )

    @staticmethod
    def api_key_created(
        db: Session,
        user_id: str,
        key_id: str,
        key_name: str,
        **kwargs
    ):
        """Publish api_key.created event"""
        event_data = {
            "api_key_id": key_id,
            "key_name": key_name,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.API_KEY_CREATED.value, event_data,
            f"API key '{key_name}' created"
        )

    @staticmethod
    def api_key_revoked(
        db: Session,
        user_id: str,
        key_id: str,
        key_name: str,
        **kwargs
    ):
        """Publish api_key.revoked event"""
        event_data = {
            "api_key_id": key_id,
            "key_name": key_name,
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.API_KEY_REVOKED.value, event_data,
            f"API key '{key_name}' revoked"
        )

    # =========================================================================
    # Supplier Events
    # =========================================================================

    @staticmethod
    def supplier_created(
        db: Session,
        user_id: str,
        supplier_id: str,
        name: str,
        supplier_type: str,
        **kwargs
    ):
        """Publish supplier.created event"""
        event_data = {
            "supplier_id": supplier_id,
            "name": name,
            "supplier_type": supplier_type,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.SUPPLIER_CREATED.value, event_data,
            f"Supplier '{name}' created"
        )

    @staticmethod
    def supplier_updated(
        db: Session,
        user_id: str,
        supplier_id: str,
        name: str,
        changes: dict,
        **kwargs
    ):
        """Publish supplier.updated event"""
        event_data = {
            "supplier_id": supplier_id,
            "name": name,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.SUPPLIER_UPDATED.value, event_data,
            f"Supplier '{name}' updated"
        )

    @staticmethod
    def supplier_deleted(
        db: Session,
        user_id: str,
        supplier_id: str,
        name: str,
        **kwargs
    ):
        """Publish supplier.deleted event"""
        event_data = {
            "supplier_id": supplier_id,
            "name": name,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.SUPPLIER_DELETED.value, event_data,
            f"Supplier '{name}' deleted"
        )

    # =========================================================================
    # Supplier Quote Events
    # =========================================================================

    @staticmethod
    def quote_created(
        db: Session,
        user_id: str,
        quote_id: str,
        supplier_id: str,
        part_id: str,
        unit_price: float,
        lead_time_days: int,
        **kwargs
    ):
        """Publish quote.created event"""
        event_data = {
            "quote_id": quote_id,
            "supplier_id": supplier_id,
            "part_id": part_id,
            "unit_price": unit_price,
            "lead_time_days": lead_time_days,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.QUOTE_CREATED.value, event_data,
            f"Quote {quote_id} created for supplier"
        )

    @staticmethod
    def quote_updated(
        db: Session,
        user_id: str,
        quote_id: str,
        supplier_id: str,
        part_id: str,
        changes: dict,
        **kwargs
    ):
        """Publish quote.updated event"""
        event_data = {
            "quote_id": quote_id,
            "supplier_id": supplier_id,
            "part_id": part_id,
            "changes": changes,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.QUOTE_UPDATED.value, event_data,
            f"Quote {quote_id} updated"
        )

    @staticmethod
    def quote_deleted(
        db: Session,
        user_id: str,
        quote_id: str,
        supplier_id: str,
        part_id: str,
        **kwargs
    ):
        """Publish quote.deleted event"""
        event_data = {
            "quote_id": quote_id,
            "supplier_id": supplier_id,
            "part_id": part_id,
            **kwargs
        }
        EventPublisher.publish(
            db, user_id, WebhookEventType.QUOTE_DELETED.value, event_data,
            f"Quote {quote_id} deleted"
        )
