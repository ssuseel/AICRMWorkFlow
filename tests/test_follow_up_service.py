"""Follow-up scheduling and lifecycle tests."""

from datetime import UTC, datetime, timedelta

from src.db.models import Lead, Tenant
from src.domain.schemas import FollowUpCreate
from src.services.follow_up_service import FollowUpService


def create_lead(session):
    tenant = Tenant(name="Follow-ups", slug="follow-up-test")
    session.add(tenant)
    session.flush()
    lead = Lead(
        tenant_id=tenant.id,
        first_name="Grace",
        last_name="Hopper",
        email="grace.follow@example.com",
        company="Navy",
        status="QUALIFIED",
        source="Referral",
    )
    session.add(lead)
    session.commit()
    return tenant, lead


def test_business_day_calculation_skips_weekends():
    friday = datetime(2026, 11, 20, 12, tzinfo=UTC)
    assert (
        FollowUpService.add_business_days(friday, 3).date().isoformat() == "2026-11-25"
    )


def test_create_reschedule_complete_and_due_tracking(session):
    tenant, lead = create_lead(session)
    service = FollowUpService(session, tenant.id)
    due = datetime.now(UTC) + timedelta(days=2)
    follow_up = service.create(
        FollowUpCreate(
            lead_id=lead.id,
            title="Review proposal",
            priority="high",
            due_at=due,
        )
    )
    assert follow_up.status == "OPEN"

    rescheduled = service.reschedule(
        follow_up.id,
        datetime.now(UTC) + timedelta(days=5),
    )
    assert rescheduled.status == "SCHEDULED"
    assert lead.next_follow_up_at == rescheduled.due_at

    completed = service.complete(follow_up.id)
    assert completed.status == "COMPLETED"
    assert completed.completed_at is not None
    assert lead.next_follow_up_at is None


def test_mark_overdue_and_cancel(session):
    tenant, lead = create_lead(session)
    service = FollowUpService(session, tenant.id)
    follow_up = service.schedule_business_follow_up(
        lead.id,
        "Introductory call",
        days=1,
    )
    follow_up.due_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    count = service.mark_overdue()
    assert count == 1
    assert follow_up.status == "OVERDUE"

    cancelled = service.cancel(follow_up.id, "Customer responded")
    assert cancelled.status == "CANCELLED"
    assert cancelled.cancellation_reason == "Customer responded"
