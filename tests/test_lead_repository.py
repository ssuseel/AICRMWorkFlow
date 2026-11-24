"""Lead repository filtering and tenant isolation tests."""

from src.db.models import Lead, Tenant
from src.repositories.lead_repository import LeadRepository


def test_search_filters_by_status_source_industry_and_score(session):
    tenant = Tenant(name="Tenant", slug="tenant-search")
    other = Tenant(name="Other", slug="tenant-other")
    session.add_all([tenant, other])
    session.flush()
    matching = Lead(
        tenant_id=tenant.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada-search@example.com",
        company="Analytical Engines",
        industry="Technology",
        source="Webinar",
        status="QUALIFIED",
        qualification_score=90,
    )
    foreign = Lead(
        tenant_id=other.id,
        first_name="Foreign",
        last_name="Lead",
        email="foreign@example.com",
        industry="Technology",
        source="Webinar",
        status="QUALIFIED",
        qualification_score=95,
    )
    session.add_all([matching, foreign])
    session.commit()

    repository = LeadRepository(session, tenant.id)
    rows, total = repository.search(
        industry="Technology",
        source="Webinar",
        status="QUALIFIED",
        min_score=80,
        max_score=100,
    )
    assert total == 1
    assert rows[0].id == matching.id
