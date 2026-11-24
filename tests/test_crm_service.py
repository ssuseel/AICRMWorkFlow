"""CRM service idempotency, isolation, and retry tests."""

from datetime import UTC, datetime, timedelta

from src.db.models import AuditEvent, Lead, Tenant
from src.domain.schemas import CRMUpsertResult
from src.integrations.crm.base import (
    CRMPermanentError,
    CRMTransientError,
)
from src.integrations.crm.mock_provider import MockCRMProvider
from src.services.crm_service import CRMService


class FirstAttemptTransientProvider(MockCRMProvider):
    provider_name = "retry-test"

    def __init__(self):
        super().__init__()
        self.fail_once = True

    def upsert_lead(self, lead, field_mapping, idempotency_key):
        if self.fail_once:
            self.fail_once = False
            raise CRMTransientError("Temporary outage")
        return CRMUpsertResult(
            provider=self.provider_name,
            external_id="retry-record",
            entity_type="lead",
            created=True,
        )


def create_lead(session, tenant, email="crm@example.com"):
    lead = Lead(
        tenant_id=tenant.id,
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        company="Analytical Engines",
        status="QUALIFIED",
        source="Referral",
    )
    session.add(lead)
    session.commit()
    return lead


def test_mock_sync_is_idempotent_and_audited(session):
    MockCRMProvider.clear_records()
    tenant = Tenant(name="CRM", slug="crm-sync")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant)
    service = CRMService(session, tenant.id, MockCRMProvider())

    first = service.sync_lead(lead.id)
    second = service.sync_lead(lead.id)

    assert first.status == "SYNCED"
    assert first.external_id.startswith("mock-lead-")
    assert first.id == second.id
    assert (
        session.query(AuditEvent)
        .filter_by(tenant_id=tenant.id, action="crm_sync_succeeded")
        .count()
        == 1
    )


def test_crm_service_rejects_cross_tenant_lead(session):
    own_tenant = Tenant(name="Own", slug="crm-own")
    other_tenant = Tenant(name="Other", slug="crm-other")
    session.add_all([own_tenant, other_tenant])
    session.flush()
    foreign_lead = create_lead(session, other_tenant, "foreign-crm@example.com")
    service = CRMService(session, own_tenant.id, MockCRMProvider())

    try:
        service.sync_lead(foreign_lead.id)
    except LookupError:
        pass
    else:
        raise AssertionError("Cross-tenant lead was synchronized")


def test_transient_failure_is_scheduled_and_can_be_retried(session):
    MockCRMProvider.clear_records()
    tenant = Tenant(name="Retry", slug="crm-retry")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant, "retry-crm@example.com")
    provider = FirstAttemptTransientProvider()
    service = CRMService(session, tenant.id, provider)

    failed = service.sync_lead(lead.id)
    assert failed.status == "RETRY_SCHEDULED"
    assert failed.attempt_count == 1
    assert failed.next_retry_at is not None

    failed.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert service.retry_due() == 1
    assert failed.status == "SYNCED"
    assert failed.attempt_count == 2


def test_permanent_failure_is_persisted(session):
    tenant = Tenant(name="Permanent", slug="crm-permanent")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant, "permanent@example.com")

    class PermanentProvider(MockCRMProvider):
        provider_name = "permanent-test"

        def upsert_lead(self, lead, field_mapping, idempotency_key):
            raise CRMPermanentError("Invalid CRM field mapping")

    service = CRMService(session, tenant.id, PermanentProvider())
    record = service.sync_lead(lead.id)
    assert record.status == "PERMANENT_FAILURE"
    assert record.last_error == "Invalid CRM field mapping"


def test_field_mapping_is_saved_tenant_scoped_and_used(session):
    tenant = Tenant(name="Mapping", slug="crm-mapping")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant, "mapping@example.com")
    service = CRMService(session, tenant.id, MockCRMProvider())

    mapping = service.set_field_mapping("industry", "Industry__c")
    assert mapping.provider == "mock"
    assert service._mapping()["industry"] == "Industry__c"
    record = service.sync_lead(lead.id)
    assert record.status == "SYNCED"


def test_mock_sync_associates_contact_with_account(session):
    MockCRMProvider.clear_records()
    tenant = Tenant(name="Association", slug="crm-association")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant, "association@example.com")
    provider = MockCRMProvider()
    service = CRMService(session, tenant.id, provider)

    contact, account = service.sync_contact_and_account(lead.id)

    assert contact.entity_type == "contact"
    assert account.entity_type == "account"
    contact_record = next(
        record
        for record in provider.records.values()
        if record["id"] == contact.external_id
    )
    assert contact_record["AccountId"] == account.external_id
