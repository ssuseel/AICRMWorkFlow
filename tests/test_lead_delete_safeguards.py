"""Lead deletion safeguard tests."""

from src.db.models import FollowUp, Tenant
from src.domain.schemas import LeadCreate
from src.services.lead_service import LeadDeleteRestrictedError, LeadService


def test_active_followup_prevents_lead_deletion(session):
    tenant = Tenant(name="Tenant", slug="tenant-delete")
    session.add(tenant)
    session.flush()
    service = LeadService(session, tenant.id)
    lead = service.create(
        LeadCreate(
            first_name="Charles",
            last_name="Babbage",
            email="charles@example.com",
        )
    )
    follow_up = FollowUp(
        tenant_id=tenant.id,
        lead_id=lead.id,
        title="Call",
        status="OPEN",
        due_at=lead.created_at,
    )
    session.add(follow_up)
    session.commit()

    try:
        service.soft_delete(lead.id)
    except LeadDeleteRestrictedError:
        pass
    else:
        raise AssertionError("Lead deletion bypassed active follow-up safeguard")
