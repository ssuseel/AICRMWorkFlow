"""Lead service tests."""

from src.db.models import Tenant, User
from src.domain.schemas import LeadCreate, LeadUpdate
from src.services.lead_service import DuplicateLeadError, LeadService


def test_duplicate_lead_is_rejected(session):
    tenant = Tenant(name="Test", slug="test-leads")
    session.add(tenant)
    session.flush()
    service = LeadService(session, tenant.id)
    data = LeadCreate(
        first_name="Ada",
        last_name="Lovelace",
        email="Ada@Example.com",
        company="Analytical Engines",
    )

    lead = service.create(data)
    assert lead.email == "ada@example.com"

    try:
        service.create(data)
    except DuplicateLeadError:
        pass
    else:
        raise AssertionError("Duplicate lead was accepted")


def test_update_assignment_status_and_score(session):
    tenant = Tenant(name="Test", slug="test-update")
    session.add(tenant)
    session.flush()
    owner = User(
        tenant_id=tenant.id,
        email="owner@example.com",
        display_name="Owner",
    )
    session.add(owner)
    session.flush()
    service = LeadService(session, tenant.id)
    lead = service.create(
        LeadCreate(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
        )
    )

    updated = service.update(
        lead.id,
        LeadUpdate(
            company="Navy",
            owner_id=owner.id,
            status="QUALIFIED",
            qualification_score=84,
        ),
    )
    assert updated.company == "Navy"
    assert updated.owner_id == owner.id
    assert updated.status == "QUALIFIED"
    assert updated.qualification_score == 84


def test_csv_import_counts_created_duplicate_and_rejected(session):
    tenant = Tenant(name="Test", slug="test-import")
    session.add(tenant)
    session.flush()
    service = LeadService(session, tenant.id)
    csv_content = (
        "first_name,last_name,email,company,industry\n"
        "Katherine,Johnson,katherine@example.com,NASA,Technology\n"
        "Katherine,Johnson,katherine@example.com,NASA,Technology\n"
        "Invalid,,missing-email,Example,Technology\n"
    )

    counts = service.import_csv(csv_content)
    assert counts["created"] == 1
    assert counts["duplicates"] == 1
    assert counts["rejected"] == 1


def test_soft_delete_marks_deleted(session):
    tenant = Tenant(name="Test", slug="test-delete")
    session.add(tenant)
    session.flush()
    service = LeadService(session, tenant.id)
    lead = service.create(
        LeadCreate(
            first_name="Alan",
            last_name="Turing",
            email="alan@example.com",
        )
    )

    deleted = service.soft_delete(lead.id)
    assert deleted.deleted_at is not None
    assert deleted.status == "DELETED"
