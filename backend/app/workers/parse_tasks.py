"""Skeleton for now — real parsing/scoring lands in Phase 3."""

from uuid import UUID
from app.database import SessionLocal
from app.models import Statement
from app.workers.celery_app import celery_app


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