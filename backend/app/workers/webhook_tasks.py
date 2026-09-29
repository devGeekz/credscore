"""Celery wrapper for webhook delivery — retry policy lives here, the HTTP
attempt lives in services.webhook_service."""

import logging

from app.config import settings
from app.services.webhook_service import MAX_ATTEMPTS, DeliveryFailed, attempt_delivery
from app.workers.celery_app import celery_app

logger = logging.getLogger("credscore")


@celery_app.task(name="deliver_webhook_task", bind=True, max_retries=5)
def deliver_webhook_task(self, log_id: str):
    """3 attempts total with exponential backoff (15s, 30s, 60s)."""
    try:
        attempt_delivery(log_id)
    except DeliveryFailed as exc:
        if exc.attempts >= MAX_ATTEMPTS:
            logger.error(
                "Webhook %s failed after %d attempts (%s)",
                log_id,
                exc.attempts,
                exc,
            )
            return
        if settings.environment == "development":
            # ponytail: no broker locally — don't sit on a backoff nobody runs
            logger.warning("Webhook %s failed (%s); no broker, not retrying", log_id, exc)
            return
        raise self.retry(exc=exc, countdown=2 ** exc.attempts * 15)
