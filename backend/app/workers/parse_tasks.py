"""Skeleton for now — real parsing/scoring lands in Phase 3."""

import logging
from uuid import UUID

from app.config import settings
from app.database import SessionLocal
from app.models import Statement
from app.workers.celery_app import celery_app

logger = logging.getLogger("credscore")


@celery_app.task(name="parse_statement_task", bind=True, max_retries=3)
def parse_statement_task(self, statement_id: str):
    db = SessionLocal()
    try:
        # Task args round-trip through JSON, so statement_id always arrives
        # as a plain string — convert back to UUID before querying.
        statement = db.query(Statement).filter(Statement.id == UUID(statement_id)).first()
        if statement is None:
            return

        statement.parse_status = "parsed"
        db.commit()

    except Exception as exc:
        db.rollback()
        statement = db.query(Statement).filter(Statement.id == UUID(statement_id)).first()
        if statement:
            statement.parse_status = "failed"
            statement.parse_error = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


def queue_parse(statement_id: UUID | str) -> None:
    """Single entry point for both the web and WhatsApp ingestion paths."""
    try:
        parse_statement_task.delay(str(statement_id))
    except Exception:
        if settings.environment == "development":
            # ponytail: no broker locally — parse inline so E2E is testable
            try:
                parse_statement_task.apply(args=[str(statement_id)])
            except Exception:
                logger.exception("Inline parse failed for %s", statement_id)
        else:
            # ponytail: broker down leaves the row `pending`; re-queue endpoint
            # lands with Phase 4 status polling.
            logger.exception("Could not queue parse for %s", statement_id)