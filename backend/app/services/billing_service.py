"""Subscription plans + per-statement usage metering (Phase 5).

No payment provider is in the stack — these are the numbers the settings
dashboard displays and what billing will enforce once invoicing exists."""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Merchant, Statement, Tenant

PLAN_LIMITS: dict[str, dict] = {
    "pilot": {"statements_per_month": 50, "price_monthly": 0, "seats": 1},
    "growth": {"statements_per_month": 500, "price_monthly": 800, "seats": 5},
    "enterprise": {"statements_per_month": None, "price_monthly": None, "seats": None},
}


def plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["pilot"])


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage(db: Session, tenant: Tenant) -> dict:
    used = (
        db.query(func.count(Statement.id))
        .join(Merchant)
        .filter(Merchant.tenant_id == tenant.id, Statement.created_at >= _month_start())
        .scalar()
        or 0
    )
    limits = plan_limits(tenant.subscription_plan)
    included = limits["statements_per_month"]
    return {
        "plan": tenant.subscription_plan,
        "status": tenant.subscription_status,
        "month": _month_start().strftime("%Y-%m"),
        "statements_used": used,
        "statements_included": included,
        "overage": max(0, used - included) if included is not None else 0,
        "price_monthly": limits["price_monthly"],
        "seats": limits["seats"],
    }
