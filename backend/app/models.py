import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Numeric, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Tenant(Base):
    """A lending institution: MFI, bank, or fintech lender."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    org_type = Column(String, nullable=False)  # mfi, bank, fintech_lender
    contact_email = Column(String, nullable=False)
    subscription_plan = Column(String, default="pilot")
    subscription_status = Column(String, default="trial")
    api_key_hash = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    merchants = relationship("Merchant", back_populates="tenant")
    webhook_logs = relationship("WebhookLog", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")


class User(Base):
    """A lender-side staff account: admin, underwriter, viewer."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, underwriter, viewer
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Merchant(Base):
    """A micro-merchant/loan applicant being scored by a specific tenant."""
    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    business_name = Column(String, nullable=True)
    telco = Column(String, nullable=True)  # MTN, Telecel, AirtelTigo
    consent_verified = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="merchants")
    statements = relationship("Statement", back_populates="merchant")


class Statement(Base):
    """A raw MoMo statement file submitted for a merchant."""
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    source_channel = Column(String, nullable=False)  # whatsapp, web_upload, email
    file_url = Column(String, nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    parse_status = Column(String, default="pending")  # pending, parsed, failed
    parse_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    merchant = relationship("Merchant", back_populates="statements")
    score_report = relationship("ScoreReport", back_populates="statement", uselist=False)


class ScoreReport(Base):
    """The generated credit-intelligence output for a statement."""
    __tablename__ = "score_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("statements.id"), nullable=False)
    net_verified_revenue = Column(Numeric(12, 2), nullable=True)
    cash_flow_consistency = Column(Numeric(5, 2), nullable=True)
    average_daily_balance = Column(Numeric(12, 2), nullable=True)
    expense_ratio = Column(Numeric(5, 2), nullable=True)
    counterparty_concentration = Column(Numeric(5, 2), nullable=True)
    risk_tag = Column(String, nullable=True)  # strong, moderate, high_risk
    suggested_credit_limit = Column(Numeric(12, 2), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    statement = relationship("Statement", back_populates="score_report")


class WebhookLog(Base):
    """Outbound delivery log of score reports pushed to lender systems."""
    __tablename__ = "webhook_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    event_type = Column(String, nullable=False)  # score.completed, statement.failed
    payload = Column(JSON, nullable=False)
    response_status = Column(String, nullable=True)
    attempts = Column(String, default="0")
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="webhook_logs")


class AuditLog(Base):
    """Immutable action log for compliance (DPC / BoG audit trail)."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")