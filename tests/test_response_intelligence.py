"""Response classification and cancellation tests."""

from src.db.models import FollowUp, Lead, Tenant
from src.domain.schemas import IncomingEmail
from src.services.response_intelligence_service import ResponseIntelligenceService


def create_lead_and_followup(session):
    tenant = Tenant(name="Responses", slug="response-test")
    session.add(tenant)
    session.flush()
    lead = Lead(
        tenant_id=tenant.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada.response@example.com",
        company="Analytical Engines",
        status="CONTACTED",
        source="Website",
    )
    session.add(lead)
    session.flush()
    follow_up = FollowUp(
        tenant_id=tenant.id,
        lead_id=lead.id,
        title="Call",
        status="SCHEDULED",
        due_at=lead.created_at,
    )
    session.add(follow_up)
    session.commit()
    return tenant, lead, follow_up


def test_positive_response_is_classified_and_lead_is_engaged(session):
    tenant, lead, _ = create_lead_and_followup(session)
    service = ResponseIntelligenceService(session, tenant.id)
    incoming = IncomingEmail(
        provider_message_id="m-positive",
        thread_id="thread-positive",
        from_address="ada.response@example.com",
        to_address="sender@example.com",
        subject="Interested in a meeting",
        body="Yes, schedule a call and send the details.",
    )

    classified = service.classify(incoming)
    assert classified.classification == "meeting_request"
    assert classified.priority == "high"
    assert classified.human_review_required

    stored = service.ingest(incoming)
    assert stored.classification == "meeting_request"
    assert lead.status == "ENGAGED"


def test_unsubscribe_cancels_all_active_followups(session):
    tenant, lead, follow_up = create_lead_and_followup(session)
    service = ResponseIntelligenceService(session, tenant.id)

    response = service.ingest(
        IncomingEmail(
            provider_message_id="m-unsubscribe",
            thread_id="thread-unsubscribe",
            from_address="ada.response@example.com",
            to_address="sender@example.com",
            subject="Please unsubscribe",
            body="Remove me from your email list.",
        )
    )

    assert response.classification == "unsubscribe"
    assert response.unsubscribed
    assert follow_up.status == "CANCELLED"
    assert follow_up.cancellation_reason == "Customer unsubscribed"
    assert lead.status == "SUPPRESSED"


def test_duplicate_response_is_not_persisted_twice(session):
    tenant, _, _ = create_lead_and_followup(session)
    service = ResponseIntelligenceService(session, tenant.id)
    incoming = IncomingEmail(
        provider_message_id="m-duplicate",
        thread_id="thread-duplicate",
        from_address="ada.response@example.com",
        to_address="sender@example.com",
        subject="Pricing",
        body="Please send pricing.",
    )

    first = service.ingest(incoming)
    second = service.ingest(incoming)
    assert first.id == second.id
    assert (
        session.query(type(first)).filter(type(first).tenant_id == tenant.id).count()
        == 1
    )
