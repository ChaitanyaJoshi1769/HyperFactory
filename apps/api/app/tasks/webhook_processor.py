"""Background task processor for webhook deliveries"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.services.webhook_service import WebhookService
from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Background processor for webhook deliveries"""

    # Configuration
    BATCH_SIZE = 100  # Process this many deliveries per run
    MAX_CONCURRENT = 10  # Process this many in parallel
    CHECK_INTERVAL_SECONDS = 60  # Check for pending deliveries every X seconds

    @staticmethod
    def process_pending_deliveries(db: Session = None) -> dict:
        """
        Process pending webhook deliveries.

        Returns:
            dict with processing stats
        """
        if db is None:
            db = SessionLocal()

        try:
            # Get pending deliveries
            pending = WebhookService.get_pending_deliveries(db, limit=WebhookProcessor.BATCH_SIZE)
            logger.info(f"Processing {len(pending)} pending webhook deliveries")

            stats = {
                "total": len(pending),
                "successful": 0,
                "failed": 0,
                "errors": []
            }

            # Group deliveries by webhook
            deliveries_by_webhook = {}
            for delivery in pending:
                webhook_id = str(delivery.webhook_id)
                if webhook_id not in deliveries_by_webhook:
                    deliveries_by_webhook[webhook_id] = []
                deliveries_by_webhook[webhook_id].append(delivery)

            # Process each webhook
            for webhook_id, deliveries in deliveries_by_webhook.items():
                webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
                if not webhook:
                    logger.warning(f"Webhook {webhook_id} not found, skipping {len(deliveries)} deliveries")
                    continue

                for delivery in deliveries:
                    try:
                        success, response_time, http_status = WebhookService.deliver_webhook(
                            db, delivery.delivery_id, webhook
                        )

                        if success:
                            stats["successful"] += 1
                            logger.info(
                                f"✓ Delivered {delivery.event_type} ({response_time}ms) "
                                f"to {webhook.url} - attempt {delivery.attempt_number}"
                            )
                        else:
                            stats["failed"] += 1
                            logger.warning(
                                f"✗ Failed to deliver {delivery.event_type} to {webhook.url} "
                                f"(HTTP {http_status}) - attempt {delivery.attempt_number}"
                            )

                    except Exception as e:
                        stats["failed"] += 1
                        error_msg = f"Error delivering {delivery.delivery_id}: {str(e)}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)

            logger.info(
                f"Webhook delivery processing complete: "
                f"{stats['successful']} successful, {stats['failed']} failed"
            )

            return stats

        except Exception as e:
            logger.error(f"Error in webhook processor: {str(e)}", exc_info=True)
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "errors": [str(e)]
            }
        finally:
            if db:
                db.close()

    @staticmethod
    async def async_process_pending_deliveries(db: Session = None) -> dict:
        """
        Async version of process_pending_deliveries.
        Useful for FastAPI background tasks.
        """
        # Run in thread pool since we're using SQLAlchemy (not async)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            WebhookProcessor.process_pending_deliveries,
            db
        )

    @staticmethod
    def get_webhook_stats(db: Session = None) -> dict:
        """
        Get overall webhook statistics.

        Returns:
            dict with stats about webhooks and deliveries
        """
        if db is None:
            db = SessionLocal()

        try:
            total_webhooks = db.query(Webhook).count()
            active_webhooks = db.query(Webhook).filter(
                Webhook.status == "active",
                Webhook.deleted_at.is_(None)
            ).count()
            disabled_webhooks = db.query(Webhook).filter(
                Webhook.status == "disabled"
            ).count()

            total_deliveries = db.query(WebhookDelivery).count()
            successful_deliveries = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "success"
            ).count()
            failed_deliveries = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "failed"
            ).count()
            pending_deliveries = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "pending"
            ).count()

            return {
                "webhooks": {
                    "total": total_webhooks,
                    "active": active_webhooks,
                    "disabled": disabled_webhooks
                },
                "deliveries": {
                    "total": total_deliveries,
                    "successful": successful_deliveries,
                    "failed": failed_deliveries,
                    "pending": pending_deliveries,
                    "success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting webhook stats: {str(e)}")
            return {
                "webhooks": {},
                "deliveries": {},
                "error": str(e)
            }
        finally:
            if db:
                db.close()

    @staticmethod
    def cleanup_old_deliveries(db: Session = None, days_to_keep: int = 30) -> dict:
        """
        Clean up old webhook deliveries to save space.

        Args:
            db: Database session
            days_to_keep: Keep deliveries newer than this many days

        Returns:
            dict with cleanup stats
        """
        if db is None:
            db = SessionLocal()

        try:
            from datetime import datetime, timedelta
            from sqlalchemy import delete

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Count before deletion
            count_before = db.query(WebhookDelivery).count()

            # Delete old deliveries
            stmt = delete(WebhookDelivery).where(WebhookDelivery.created_at < cutoff_date)
            result = db.execute(stmt)
            db.commit()

            deleted_count = result.rowcount
            count_after = db.query(WebhookDelivery).count()

            stats = {
                "deleted": deleted_count,
                "before": count_before,
                "after": count_after,
                "cutoff_date": cutoff_date.isoformat()
            }

            logger.info(f"Cleaned up {deleted_count} old webhook deliveries")
            return stats

        except Exception as e:
            logger.error(f"Error cleaning up deliveries: {str(e)}")
            return {"error": str(e)}
        finally:
            if db:
                db.close()
