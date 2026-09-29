"""organisation settings: profile, plan + usage, and webhook configuration."""

import ipaddress
import re
import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.middleware.tenant import get_current_user
from app.models import Tenant, User, WebhookLog
from app.services.billing_service import usage

router = APIRouter()

# blocks the obvious ssrf targets (loopback/link-local/rfc1918, localhost
# names). a hostname resolving to a private ip still gets through —
# resolve-and-check + egress rules are the upgrade path for production.
_PRIVATE_HOST_PATTERN = re.compile(
    r"^(localhost|.*\.(local|internal|localhost))$", re.IGNORECASE
)


class SettingsOut(BaseModel):
    name: str
    org_type: str
    contact_email: str
    subscription_plan: str
    subscription_status: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    usage: dict


class SettingsUpdate(BaseModel):
    webhook_url: str = ""
    rotate_webhook_secret: bool = False


class WebhookDeliveryOut(BaseModel):
    id: str
    event_type: str
    delivered: bool
    attempts: str
    response_status: Optional[str] = None
    created_at: datetime


def _validate_webhook_url(raw: str) -> str:
    url = raw.strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="webhook_url must be http(s)")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="webhook_url must not contain credentials")
    if app_settings.environment == "development":
        # local receivers are used in dev; the guard below applies in production
        return url
    if _PRIVATE_HOST_PATTERN.match(parsed.hostname):
        raise HTTPException(status_code=400, detail="webhook_url host not allowed")
    try:
        if ipaddress.ip_address(parsed.hostname).is_private:
            raise HTTPException(status_code=400, detail="webhook_url host not allowed")
    except ValueError:
        pass  # hostname, not a literal ip
    return url


def _out(db: Session, tenant: Tenant) -> SettingsOut:
    return SettingsOut(
        name=tenant.name,
        org_type=tenant.org_type,
        contact_email=tenant.contact_email,
        subscription_plan=tenant.subscription_plan,
        subscription_status=tenant.subscription_status,
        webhook_url=tenant.webhook_url,
        webhook_secret=tenant.webhook_secret,
        usage=usage(db, tenant),
    )


@router.get("", response_model=SettingsOut)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, current_user.tenant_id)
    return _out(db, tenant)


@router.get("/webhooks", response_model=list[WebhookDeliveryOut])
def webhook_deliveries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(WebhookLog)
        .filter(WebhookLog.tenant_id == current_user.tenant_id)
        .order_by(WebhookLog.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(log.id),
            "event_type": log.event_type,
            "delivered": log.delivered,
            "attempts": log.attempts,
            "response_status": log.response_status,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, current_user.tenant_id)
    tenant.webhook_url = _validate_webhook_url(payload.webhook_url) or None
    if payload.rotate_webhook_secret or (
        tenant.webhook_url and not tenant.webhook_secret
    ):
        tenant.webhook_secret = secrets.token_urlsafe(32)
    db.commit()
    return _out(db, tenant)
