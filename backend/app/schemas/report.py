import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportMerchant(BaseModel):
    id: uuid.UUID
    full_name: str

    class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    id: uuid.UUID
    statement_id: uuid.UUID
    merchant: ReportMerchant
    risk_tag: Optional[str]
    net_verified_revenue: Optional[float]
    cash_flow_consistency: Optional[float]
    suggested_credit_limit: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportDetail(ReportSummary):
    cash_flow_consistency: Optional[float]
    average_daily_balance: Optional[float]
    expense_ratio: Optional[float]
    counterparty_concentration: Optional[float]
    source_channel: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    parse_error: Optional[str] = None
    raw_payload: Optional[dict] = None


class DashboardStats(BaseModel):
    merchants: int
    statements_this_month: int
    statements_pending: int
    reports: int
    risk_mix: dict[str, int]
    average_credit_limit: Optional[float] = None


class ApiKeyOut(BaseModel):
    """The plain key is only ever returned at creation time."""
    masked: Optional[str]
    active: bool


class ApiKeyCreated(ApiKeyOut):
    api_key: str
