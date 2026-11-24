"""Foundation model tests."""

from src.db.models import Lead, Tenant


def test_tenant_and_lead_persist(session):
    tenant = Tenant(name="Test Tenant", slug="test-tenant")
    session.add(tenant)
    session.flush()

    lead = Lead(
        tenant_id=tenant.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        company="Analytical Engines",
        status="NEW",
        source="manual",
    )
    session.add(lead)
    session.commit()

    persisted = session.get(Lead, lead.id)
    assert persisted is not None
    assert persisted.tenant_id == tenant.id
    assert persisted.status == "NEW"
