"""Persistent SQLAlchemy models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin, utcnow


def uuid_pk() -> str:
    return str(uuid4())


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="sales", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_leads_tenant_email"),
        Index("ix_leads_tenant_status", "tenant_id", "status"),
        Index("ix_leads_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_leads_tenant_source", "tenant_id", "source"),
        Index("ix_leads_tenant_industry", "tenant_id", "industry"),
        Index("ix_leads_tenant_created", "tenant_id", "created_at"),
        Index("ix_leads_tenant_followup", "tenant_id", "next_follow_up_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(150))
    industry: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(100), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="NEW", nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    qualification_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualification_status: Mapped[str | None] = mapped_column(String(30))
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id")
    )


class LeadQualification(Base, TimestampMixin):
    __tablename__ = "lead_qualifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    business_requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    customer_intent: Mapped[str | None] = mapped_column(String(100))
    product_interest: Mapped[dict] = mapped_column(JSON, default=dict)
    budget_assessment: Mapped[str | None] = mapped_column(Text)
    timeline_assessment: Mapped[str | None] = mapped_column(Text)
    authority_assessment: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_information: Mapped[list] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSON, default=list)


class Email(Base, TimestampMixin):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_emails_tenant_idempotency"
        ),
        Index("ix_emails_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    approved_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_subject: Mapped[str | None] = mapped_column(String(500))
    approved_body: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    thread_id: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailResponse(Base, TimestampMixin):
    __tablename__ = "email_responses"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_message_id", name="uq_responses_tenant_message"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id"))
    email_id: Mapped[str | None] = mapped_column(ForeignKey("emails.id"))
    provider_message_id: Mapped[str] = mapped_column(String(200), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(200))
    from_address: Mapped[str] = mapped_column(String(320), nullable=False)
    classification: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    customer_intent: Mapped[str | None] = mapped_column(String(100))
    recommended_action: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    unsubscribed: Mapped[bool] = mapped_column(default=False, nullable=False)
    raw_content: Mapped[dict] = mapped_column(JSON, default=dict)


class FollowUp(Base, TimestampMixin):
    __tablename__ = "follow_ups"
    __table_args__ = (
        Index("ix_followups_tenant_status_due", "tenant_id", "status", "due_at"),
        Index("ix_followups_tenant_owner", "tenant_id", "owner_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)


class CRMSyncRecord(Base, TimestampMixin):
    __tablename__ = "crm_sync_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_crm_tenant_idempotency"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(50), default="lead", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class CRMConnection(Base, TimestampMixin):
    __tablename__ = "crm_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    credentials_ref: Mapped[str | None] = mapped_column(String(200))


class CRMFieldMapping(Base, TimestampMixin):
    __tablename__ = "crm_mappings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "local_field",
            name="uq_crm_mapping_tenant_provider_field",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    local_field: Mapped[str] = mapped_column(String(100), nullable=False)
    remote_field: Mapped[str] = mapped_column(String(100), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
