import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.middleware.tenant import get_current_user
from app.models import Merchant, ScoreReport, Statement, User
from app.schemas.report import ReportDetail, ReportSummary
from app.utils.errors import NotFoundError

router = APIRouter()

EXPORT_COLUMNS = [
    "report_id",
    "merchant",
    "risk_tag",
    "net_verified_revenue",
    "cash_flow_consistency",
    "average_daily_balance",
    "expense_ratio",
    "counterparty_concentration",
    "suggested_credit_limit",
    "created_at",
]


def _base_query(db: Session, tenant_id: uuid.UUID):
    return (
        db.query(ScoreReport)
        .join(Statement, ScoreReport.statement_id == Statement.id)
        .join(Merchant, Statement.merchant_id == Merchant.id)
        .options(joinedload(ScoreReport.statement).joinedload(Statement.merchant))
        .filter(Merchant.tenant_id == tenant_id)
    )


def _summary(report: ScoreReport) -> dict:
    return {
        "id": report.id,
        "statement_id": report.statement_id,
        "merchant": report.statement.merchant,
        "risk_tag": report.risk_tag,
        "net_verified_revenue": float(report.net_verified_revenue or 0),
        "cash_flow_consistency": float(report.cash_flow_consistency or 0),
        "suggested_credit_limit": float(report.suggested_credit_limit or 0),
        "created_at": report.created_at,
    }


@router.get("", response_model=list[ReportSummary])
def list_reports(
    merchant_id: Optional[uuid.UUID] = None,
    risk_tag: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = _base_query(db, current_user.tenant_id).order_by(
        ScoreReport.created_at.desc()
    )
    if merchant_id is not None:
        query = query.filter(Statement.merchant_id == merchant_id)
    if risk_tag:
        query = query.filter(ScoreReport.risk_tag == risk_tag)
    return [_summary(report) for report in query.limit(limit).all()]


@router.get("/export")
def export_reports(
    risk_tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = _base_query(db, current_user.tenant_id).order_by(
        ScoreReport.created_at.desc()
    )
    if risk_tag:
        query = query.filter(ScoreReport.risk_tag == risk_tag)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for report in query.all():
        writer.writerow(
            [
                report.id,
                report.statement.merchant.full_name,
                report.risk_tag,
                report.net_verified_revenue,
                report.cash_flow_consistency,
                report.average_daily_balance,
                report.expense_ratio,
                report.counterparty_concentration,
                report.suggested_credit_limit,
                report.created_at.isoformat(),
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="credscore-reports.csv"'},
    )


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _base_query(db, current_user.tenant_id).filter(
        ScoreReport.id == report_id
    ).first()
    if report is None:
        raise NotFoundError("Report not found")

    statement = report.statement
    return {
        **_summary(report),
        "cash_flow_consistency": float(report.cash_flow_consistency or 0),
        "average_daily_balance": float(report.average_daily_balance)
        if report.average_daily_balance is not None else None,
        "expense_ratio": float(report.expense_ratio or 0),
        "counterparty_concentration": float(report.counterparty_concentration or 0),
        "source_channel": statement.source_channel,
        "period_start": statement.period_start,
        "period_end": statement.period_end,
        "parse_error": statement.parse_error,
        "raw_payload": report.raw_payload,
    }
