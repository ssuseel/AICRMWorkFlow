"""AI qualification engine tests."""

from pydantic import ValidationError

from src.db.models import Lead, LeadQualification, Tenant
from src.domain.schemas import QualificationEvidence
from src.integrations.ai.base import AIProvider
from src.integrations.ai.mock_provider import MockAIProvider
from src.services.qualification_service import QualificationService


class FailingProvider(AIProvider):
    model_name = "failing-provider"

    def extract_qualification(self, lead_context, prompt_template):
        raise TimeoutError("Provider unavailable")


class InvalidProvider(AIProvider):
    model_name = "invalid-provider"

    def extract_qualification(self, lead_context, prompt_template):
        raise ValidationError.from_exception_data(
            "invalid",
            line_errors=[],
        )


def create_lead(session, tenant, **overrides):
    values = {
        "tenant_id": tenant.id,
        "first_name": "Jordan",
        "last_name": "Rivera",
        "email": "jordan@example.com",
        "company": "Northwind",
        "industry": "Technology",
        "title": "VP Operations",
        "source": "Referral",
        "status": "NEW",
    }
    values.update(overrides)
    lead = Lead(**values)
    session.add(lead)
    session.commit()
    return lead


def test_mock_qualification_persists_evidence_and_updates_lead(session):
    tenant = Tenant(name="Test", slug="test-qualification")
    session.add(tenant)
    session.flush()
    lead = create_lead(session, tenant)

    result = QualificationService(
        session,
        tenant.id,
        MockAIProvider(),
    ).qualify(lead.id)

    persisted = (
        session.query(LeadQualification)
        .filter_by(
            tenant_id=tenant.id,
            lead_id=lead.id,
        )
        .first()
    )
    assert persisted is not None
    assert result.score >= 0
    assert persisted.score == result.score
    assert persisted.prompt_version == "qualification-v1"
    assert lead.qualification_status == result.status
    assert lead.qualification_score == result.score
    assert persisted.missing_information


def test_weighted_score_is_deterministic(session):
    evidence = QualificationEvidence(
        business_requirements=["CRM integration"],
        customer_intent="active interest",
        product_interest=["Sales automation"],
        budget_assessment="Budget confirmed",
        timeline_assessment="Purchase within 30 days",
        authority_assessment="Decision-maker confirmed",
        evidence={"company": ["Northwind"], "industry": ["Technology"]},
        missing_information=[],
    )

    assert QualificationService.calculate_score(evidence) == 100


def test_unavailable_provider_uses_conservative_fallback(session):
    tenant = Tenant(name="Fallback", slug="fallback-qualification")
    session.add(tenant)
    session.flush()
    lead = create_lead(
        session,
        tenant,
        email="fallback@example.com",
        company="Fallback Co",
    )

    result = QualificationService(
        session,
        tenant.id,
        FailingProvider(),
    ).qualify(lead.id)

    assert result.status == "QUALIFICATION_PENDING"
    assert result.evidence.summary.startswith("AI qualification unavailable")
    assert result.score < 40
    assert lead.qualification_score == result.score


def test_missing_lead_is_rejected(session):
    tenant = Tenant(name="Missing", slug="missing-lead")
    session.add(tenant)
    session.flush()

    try:
        QualificationService(
            session,
            tenant.id,
            MockAIProvider(),
        ).qualify("missing-lead-id")
    except LookupError:
        pass
    else:
        raise AssertionError("Missing lead qualification was accepted")
