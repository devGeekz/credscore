"""outbound score webhooks: log the delivery, post it to the configured
endpoint with an hmac signature, retry 3 times with backoff.

the receiver verifies authenticity with `tenants.webhook_secret`
(hmac-sha256 over the exact body bytes)."""

import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import WebhookLog
from app.utils.queue import broker_reachable

logger = logging.getLogger("credscore")

SIGNATURE_HEADER = "X-CredScore-Signature"
EVENT_HEADER = "X-CredScore-Event"
DELIVERY_HEADER = "X-CredScore-Delivery"
MAX_ATTEMPTS = 3


class DeliveryFailed(Exception):
    """transport-level failure; carries how many attempts have been made."""

    def __init__(self, attempts: int, cause: Exception):
        self.attempts = attempts
        super().__init__(str(cause))


def sign_body(body: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


def fire_event(db: Session, tenant_id, event_type: str, payload: dict) -> None:
    """creates the delivery log, commits it, then queues the attempt.
    committing first matters: the delivery task reads this row."""
    log = WebhookLog(
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload,
        attempts="0",
        delivered=False,
    )
    db.add(log)
    db.commit()
    queue_delivery(log.id)


def queue_delivery(log_id) -> None:
    from app.workers.webhook_tasks import deliver_webhook_task

    if not broker_reachable():
        if settings.environment == "development":
            # no broker locally — deliver inline so the flow is testable
            try:
                deliver_webhook_task.apply(args=[str(log_id)])
            except Exception:
                logger.exception("Inline webhook delivery failed for %s", log_id)
        else:
            logger.error("Broker unreachable, webhook %s not queued", log_id)
        return

    try:
        deliver_webhook_task.delay(str(log_id))
    except Exception:
        logger.exception("Could not queue webhook %s", log_id)


def attempt_delivery(log_id) -> None:
    """one http attempt. raises DeliveryFailed on transport error so the
    task can decide whether to retry; a non-2xx status is not retried —
    the receiver rejected the payload, retrying will not change that."""
    from uuid import UUID

    from app.database import SessionLocal
    from app.models import Tenant

    # task args round-trip through json, so log_id arrives as a plain string
    if isinstance(log_id, str):
        log_id = UUID(log_id)

    db = SessionLocal()
    try:
        log = db.query(WebhookLog).filter(WebhookLog.id == log_id).first()
        if log is None or log.delivered:
            return
        tenant = db.query(Tenant).filter(Tenant.id == log.tenant_id).first()
        if tenant is None or not tenant.webhook_url:
            logger.info("No webhook URL for tenant %s, skipping", log.tenant_id)
            return

        attempt = int(log.attempts or "0") + 1
        log.attempts = str(attempt)
        db.commit()

        body = json.dumps(log.payload, default=str)
        headers = {
            "Content-Type": "application/json",
            EVENT_HEADER: log.event_type,
            DELIVERY_HEADER: str(log.id),
            SIGNATURE_HEADER: sign_body(body, tenant.webhook_secret or ""),
        }
        try:
            response = httpx.post(
                tenant.webhook_url, content=body, headers=headers, timeout=10
            )
        except Exception as exc:
            log.response_status = f"error: {type(exc).__name__}"
            db.commit()
            raise DeliveryFailed(attempt, exc) from exc

        log.response_status = str(response.status_code)
        log.delivered = response.is_success
        db.commit()
    finally:
        db.close()
