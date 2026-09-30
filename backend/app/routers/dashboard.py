import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.tenant import get_current_user
from app.models import Merchant, ScoreReport, Statement, User
from app.schemas.report import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    merchants = (
        db.query(func.count(Merchant.id)).filter(Merchant.tenant_id == tenant_id).scalar()
    )
    statements_total, statements_pending = (
        db.query(
            func.count(Statement.id),
            func.sum(case((Statement.parse_status == "pending", 1), else_=0)),
        )
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant_id)
        .one()
    )

    month_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(day=1)
    statements_this_month = (
        db.query(func.count(Statement.id))
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant_id, Statement.created_at >= month_start)
        .scalar()
    )

    risk_rows = (
        db.query(ScoreReport.risk_tag, func.count(ScoreReport.id))
        .join(Statement)
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant_id)
        .group_by(ScoreReport.risk_tag)
        .all()
    )
    risk_mix = {tag or "unscored": count for tag, count in risk_rows}

    average_limit = (
        db.query(func.avg(ScoreReport.suggested_credit_limit))
        .join(Statement)
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant_id)
        .scalar()
    )

    return DashboardStats(
        merchants=merchants or 0,
        statements_this_month=statements_this_month or 0,
        statements_pending=statements_pending or 0,
        reports=sum(risk_mix.values()),
        risk_mix=risk_mix,
        average_credit_limit=float(average_limit) if average_limit is not None else None,
    )


@router.get("/consent-export")
def consent_export(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """dpc-aligned consent audit: one csv row per applicant."""
    tenant_id = current_user.tenant_id
    merchants = (
        db.query(Merchant)
        .filter(Merchant.tenant_id == tenant_id)
        .order_by(Merchant.created_at.asc())
        .all()
    )

    # asc order means the last status seen per merchant is its latest
    statement_info: dict = {}
    statements = (
        db.query(Statement)
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant_id)
        .order_by(Statement.created_at.asc())
        .all()
    )
    for statement in statements:
        entry = statement_info.setdefault(statement.merchant_id, [0, ""])
        entry[0] += 1
        entry[1] = statement.parse_status

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "merchant_id", "full_name", "phone", "business_name",
        "consent_verified", "consent_timestamp",
        "statement_count", "latest_parse_status",
    ])
    for merchant in merchants:
        count, status = statement_info.get(merchant.id, [0, ""])
        writer.writerow([
            merchant.id,
            merchant.full_name,
            merchant.phone,
            merchant.business_name or "",
            merchant.consent_verified,
            merchant.consent_timestamp.isoformat() if merchant.consent_timestamp else "",
            count,
            status,
        ])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="consent-audit.csv"'},
    )
