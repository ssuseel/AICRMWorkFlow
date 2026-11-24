"""Fixture-backed analytics metric and tenant-isolation tests."""

from datetime import UTC, date, datetime

from src.db.models import (
    CRMSyncRecord,
    Email,
    EmailResponse,
    FollowUp,
    Lead,
    Tenant,
    User,
)
from src.domain.analytics import AnalyticsFilters
from src.services.analytics_service import AnalyticsService


def create_lead(session, tenant, owner, email, status, score, created_at):
    lead = Lead(
        tenant_id=tenant.id,
        owner_id=owner.id,
        first_name=email.split("@")[0],
        last_name="Example",
        email=email,
        company="Example Company",
        industry="Technology",
        source="Referral",
        status=status,
        qualification_score=score,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(lead)
    session.flush()
    return lead


def test_analytics_aggregates_use_real_tenant_data(session):
    tenant = Tenant(name="Analytics", slug="analytics")
    other_tenant = Tenant(name="Other", slug="analytics-other")
    session.add_all([tenant, other_tenant])
    session.flush()
    owner = User(
        tenant_id=tenant.id,
        email="owner@analytics.example",
        display_name="Analytics Owner",
    )
    other_owner = User(
        tenant_id=other_tenant.id,
        email="owner@other.example",
        display_name="Other Owner",
    )
    session.add_all([owner, other_owner])
    session.flush()

    created = datetime(2026, 11, 10, 12, tzinfo=UTC)
    customer = create_lead(
        session,
        tenant,
        owner,
        "customer@analytics.example",
        "CUSTOMER",
        85,
        created,
    )
    qualified = create_lead(
        session,
        tenant,
        owner,
        "qualified@analytics.example",
        "QUALIFIED",
        55,
        created,
    )
    create_lead(
        session,
        other_tenant,
        other_owner,
        "foreign@other.example",
        "CUSTOMER",
        95,
        created,
    )

    sent = Email(
        tenant_id=tenant.id,
        lead_id=customer.id,
        subject="Hello",
        body="Hi",
        status="SENT",
        provider="mock",
        provider_message_id="sent-message-1",
        sent_at=created,
        created_at=created,
        updated_at=created,
    )
    failed = Email(
        tenant_id=tenant.id,
        lead_id=qualified.id,
        subject="Hello",
        body="Hi",
        status="DELIVERY_FAILED",
        provider="mock",
        created_at=created,
        updated_at=created,
    )
    session.add_all([sent, failed])
    session.flush()
    session.add(
        EmailResponse(
            tenant_id=tenant.id,
            lead_id=customer.id,
            email_id=sent.id,
            provider_message_id="response-message-1",
            from_address=customer.email,
            classification="positive_interest",
            summary="Interested",
            priority="high",
            created_at=created,
            updated_at=created,
        )
    )
    session.add_all(
        [
            FollowUp(
                tenant_id=tenant.id,
                lead_id=customer.id,
                owner_id=owner.id,
                title="Completed follow-up",
                status="COMPLETED",
                due_at=created,
                completed_at=created,
                created_at=created,
                updated_at=created,
            ),
            FollowUp(
                tenant_id=tenant.id,
                lead_id=qualified.id,
                owner_id=owner.id,
                title="Overdue follow-up",
                status="OVERDUE",
                due_at=created,
                created_at=created,
                updated_at=created,
            ),
            CRMSyncRecord(
                tenant_id=tenant.id,
                lead_id=customer.id,
                provider="mock",
                external_id="mock-1",
                entity_type="lead",
                status="SYNCED",
                attempt_count=1,
                idempotency_key="analytics-crm-1",
                created_at=created,
                updated_at=created,
            ),
            CRMSyncRecord(
                tenant_id=tenant.id,
                lead_id=qualified.id,
                provider="mock",
                entity_type="lead",
                status="RETRY_SCHEDULED",
                attempt_count=1,
                idempotency_key="analytics-crm-2",
                created_at=created,
                updated_at=created,
            ),
        ]
    )
    session.commit()

    filters = AnalyticsFilters(
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        owner_id=owner.id,
        industry="Technology",
        source="Referral",
    )
    summary = AnalyticsService(session, tenant.id).summary(filters)

    assert summary["conversion"] == {
        "leads": 2,
        "customers": 1,
        "conversion_rate": 0.5,
    }
    assert summary["email"] == {
        "sent": 1,
        "attempted": 2,
        "responses": 1,
        "delivery_rate": 0.5,
        "response_rate": 1.0,
    }
    assert summary["follow_ups"] == {
        "total": 2,
        "completed": 1,
        "overdue": 1,
        "converted_leads": 1,
        "completion_rate": 0.5,
    }
    assert summary["crm_health"] == [
        {"status": "RETRY_SCHEDULED", "records": 1},
        {"status": "SYNCED", "records": 1},
    ]
    assert {
        row["score_band"]: row["leads"] for row in summary["qualification_distribution"]
    } == {
        "40-69": 1,
        "70-100": 1,
    }
    assert summary["acquisition_trends"] == [{"date": "2026-11-10", "leads": 2}]
    assert {row["owner"] for row in summary["team_productivity"]} == {"Analytics Owner"}


def test_analytics_filters_and_empty_metrics_are_tenant_scoped(session):
    tenant = Tenant(name="Empty Analytics", slug="empty-analytics")
    foreign = Tenant(name="Foreign Analytics", slug="foreign-analytics")
    session.add_all([tenant, foreign])
    session.flush()
    owner = User(
        tenant_id=foreign.id,
        email="foreign-owner@example.com",
        display_name="Foreign Owner",
    )
    session.add(owner)
    session.flush()
    create_lead(
        session,
        foreign,
        owner,
        "foreign-analytics@example.com",
        "CUSTOMER",
        99,
        datetime.now(UTC),
    )

    summary = AnalyticsService(session, tenant.id).summary(AnalyticsFilters())
    assert summary["conversion"]["leads"] == 0
    assert summary["conversion"]["customers"] == 0
    assert summary["conversion"]["conversion_rate"] == 0
    assert summary["email"]["delivery_rate"] == 0
    assert summary["email"]["response_rate"] == 0
    assert summary["pipeline"] == []
    assert summary["team_productivity"] == []


def test_analytics_filter_rejects_reversed_date_range():
    try:
        AnalyticsFilters(
            start_date=date(2026, 11, 30),
            end_date=date(2026, 11, 1),
        )
    except ValueError as exc:
        assert "start_date" in str(exc)
    else:
        raise AssertionError("Reversed date range was accepted")


def test_status_filter_limits_pipeline_and_conversion_cohort(session):
    tenant = Tenant(name="Status Filter", slug="analytics-status")
    session.add(tenant)
    session.flush()
    owner = User(
        tenant_id=tenant.id,
        email="status-owner@example.com",
        display_name="Status Owner",
    )
    session.add(owner)
    session.flush()
    created = datetime(2026, 11, 12, 12, tzinfo=UTC)
    create_lead(
        session,
        tenant,
        owner,
        "status-customer@example.com",
        "CUSTOMER",
        90,
        created,
    )
    create_lead(
        session,
        tenant,
        owner,
        "status-qualified@example.com",
        "QUALIFIED",
        75,
        created,
    )
    session.commit()

    summary = AnalyticsService(session, tenant.id).summary(
        AnalyticsFilters(status="QUALIFIED")
    )
    assert summary["conversion"]["leads"] == 1
    assert summary["conversion"]["customers"] == 0
    assert summary["pipeline"] == [{"status": "QUALIFIED", "leads": 1}]
