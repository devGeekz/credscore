"""statement ingestion pipeline: download -> extract -> normalize ->
classify -> score -> persist a ScoreReport."""

import logging
from uuid import UUID

from app.config import settings
from app.database import SessionLocal
from app.engine.extract import extract_dataframe
from app.engine.heuristics import classify_flows
from app.engine.normalize import normalize
from app.engine.scoring_model import score
from app.models import ScoreReport, Statement
from app.services.storage_service import download_statement_file
from app.services.webhook_service import fire_event
from app.utils.queue import broker_reachable
from app.workers.celery_app import celery_app

logger = logging.getLogger("credscore")


@celery_app.task(name="parse_statement_task", bind=True, max_retries=3)
def parse_statement_task(self, statement_id: str):
    db = SessionLocal()
    try:
        # task args round-trip through json, so statement_id always arrives
        # as a plain string — convert back to uuid before querying.
        statement = db.query(Statement).filter(Statement.id == UUID(statement_id)).first()
        if statement is None:
            return

        metrics, (period_start, period_end) = _score_statement(statement)
        report = _persist(db, statement, metrics, period_start, period_end)
        _notify_lender(db, statement, report)

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
    """single entry point for both the web and whatsapp ingestion paths."""
    if not broker_reachable():
        if settings.environment == "development":
            # no broker locally — parse inline so the flow is testable
            try:
                parse_statement_task.apply(args=[str(statement_id)])
            except Exception:
                logger.exception("Inline parse failed for %s", statement_id)
        else:
            # broker down leaves the row `pending`; the re-queue endpoint
            # lands with status polling.
            logger.error("Broker unreachable, statement %s left pending", statement_id)
        return

    try:
        parse_statement_task.delay(str(statement_id))
    except Exception:
        logger.exception("Could not queue parse for %s", statement_id)


def _score_statement(statement: Statement) -> tuple[dict, tuple]:
    data = download_statement_file(statement.file_url)
    raw = extract_dataframe(data, statement.file_url)
    flows = classify_flows(normalize(raw))
    return score(flows), (flows["ts"].min(), flows["ts"].max())


def _persist(db, statement: Statement, metrics: dict, period_start, period_end) -> ScoreReport:
    # upsert: a retried task must not create a second report for one statement.
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
    return report


def _notify_lender(db, statement: Statement, report: ScoreReport) -> None:
    tenant = statement.merchant.tenant
    if not tenant.webhook_url:
        return

    fire_event(db, tenant.id, "score.completed", {
        "report_id": str(report.id),
        "statement_id": str(statement.id),
        "merchant": {
            "id": str(statement.merchant.id),
            "full_name": statement.merchant.full_name,
            "phone": statement.merchant.phone,
        },
        "score": {
            "risk_tag": report.risk_tag,
            "net_verified_revenue": float(report.net_verified_revenue or 0),
            "cash_flow_consistency": float(report.cash_flow_consistency or 0),
            "average_daily_balance": float(report.average_daily_balance)
            if report.average_daily_balance is not None else None,
            "expense_ratio": float(report.expense_ratio or 0),
            "counterparty_concentration": float(report.counterparty_concentration or 0),
            "suggested_credit_limit": float(report.suggested_credit_limit or 0),
        },
        "period": {
            "start": statement.period_start.isoformat() if statement.period_start else None,
            "end": statement.period_end.isoformat() if statement.period_end else None,
        },
        "scored_at": report.created_at.isoformat(),
    })
