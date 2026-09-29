import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
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
