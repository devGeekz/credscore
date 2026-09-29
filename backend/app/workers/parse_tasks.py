"""Statement ingestion pipeline: download -> extract -> normalize ->
classify -> score -> persist a ScoreReport."""

import logging
import socket
from urllib.parse import urlparse
from uuid import UUID

from app.config import settings
from app.database import SessionLocal
from app.engine.extract import extract_dataframe
from app.engine.heuristics import classify_flows
from app.engine.normalize import normalize
from app.engine.scoring_model import score
from app.models import ScoreReport, Statement
from app.services.storage_service import download_statement_file
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

        metrics, (period_start, period_end) = _score_statement(statement)
        _persist(db, statement, metrics, period_start, period_end)

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


def queue_parse(statement_id) -> None:
    """Single entry point for both the web and WhatsApp ingestion paths."""
    if not _broker_reachable():
        if settings.environment == "development":
            # ponytail: no broker locally — parse inline so E2E is testable
            try:
                parse_statement_task.apply(args=[str(statement_id)])
            except Exception:
                logger.exception("Inline parse failed for %s", statement_id)
        else:
            # ponytail: broker down leaves the row `pending`; re-queue endpoint
            # lands with Phase 4 status polling.
            logger.error("Broker unreachable, statement %s left pending", statement_id)
        return

    try:
        parse_statement_task.delay(str(statement_id))
    except Exception:
        logger.exception("Could not queue parse for %s", statement_id)


def _broker_reachable(timeout: float = 0.25) -> bool:
    """Probe before publishing. Celery's publish+result-backend retries block
    for ~110s when Redis is down — an API request must not absorb that."""
    parsed = urlparse(settings.redis_url)
    address = (parsed.hostname or "localhost", parsed.port or 6379)
    try:
        with socket.create_connection(address, timeout=timeout):
            return True
    except OSError:
        return False


def _score_statement(statement: Statement) -> tuple[dict, tuple]:
    data = download_statement_file(statement.file_url)
    raw = extract_dataframe(data, statement.file_url)
    flows = classify_flows(normalize(raw))
    return score(flows), (flows["ts"].min(), flows["ts"].max())


def _persist(db, statement: Statement, metrics: dict, period_start, period_end) -> None:
    # Upsert: a retried task must not create a second report for one statement.
    report = db.query(ScoreReport).filter(ScoreReport.statement_id == statement.id).first()
    if report is None:
        report = ScoreReport(statement_id=statement.id)
        db.add(report)
    for key, value in metrics.items():
        setattr(report, key, value)

    statement.parse_status = "parsed"
    statement.parse_error = None
    statement.period_start = period_start.to_pydatetime()
    statement.period_end = period_end.to_pydatetime()
    db.commit()
