"""Email drafting and approval restriction tests."""

from uuid import UUID

from src.db.models import Lead, Tenant, User
from src.domain.schemas import EmailDraftCreate, EmailDraftUpdate
from src.integrations.email.mock_provider import MockEmailProvider
from src.services.email_service import (
    EmailApprovalRequiredError,
    EmailService,
    EmailWorkflowError,
)


def create_email_fixture(session):
    tenant = Tenant(name="Email Test", slug="email-test")
    session.add(tenant)
    session.flush()
    lead = Lead(
        tenant_id=tenant.id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        company="Analytical Engines",
        status="NEW",
        source="Website",
    )
    approver = User(
        tenant_id=tenant.id,
        email="approver@example.com",
        display_name="Demo Approver",
        role="manager",
    )
    session.add_all([lead, approver])
    session.flush()
    return tenant, lead, approver


def test_draft_preview_edit_and_approval_snapshot(session):
    tenant, lead, approver = create_email_fixture(session)
    service = EmailService(session, tenant.id, MockEmailProvider())

    draft = service.create_draft(
        EmailDraftCreate(
            lead_id=UUID(lead.id),
            subject="Initial subject",
            body="Initial body",
        )
    )
    preview = service.preview(draft.id)
    assert preview["to"] == "ada@example.com"

    updated = service.update_draft(
        draft.id,
        EmailDraftUpdate(subject="Edited subject", body="Edited body"),
    )
    assert updated.status == "DRAFT"
    assert updated.subject == "Edited subject"

    submitted = service.submit_for_approval(draft.id)
    assert submitted.status == "PENDING_APPROVAL"
    approved = service.approve(draft.id, approver.id)
    assert approved.status == "APPROVED"
    assert approved.approved_subject == "Edited subject"
    assert approved.approved_body == "Edited body"
    assert approved.approved_by_id == approver.id


def test_send_requires_human_approval(session):
    tenant, lead, _ = create_email_fixture(session)
    service = EmailService(session, tenant.id, MockEmailProvider())
    draft = service.create_draft(
        EmailDraftCreate(
            lead_id=UUID(lead.id),
            subject="Subject",
            body="Body",
        )
    )

    try:
        service.send(draft.id)
    except EmailApprovalRequiredError:
        pass
    else:
        raise AssertionError("Unapproved email was sent")


def test_mock_send_is_persistent_and_idempotent_key_is_stored(session):
    tenant, lead, approver = create_email_fixture(session)
    service = EmailService(session, tenant.id, MockEmailProvider())
    draft = service.generate_demo_draft(lead.id)
    service.submit_for_approval(draft.id)
    service.approve(draft.id, approver.id)

    sent = service.send(draft.id, idempotency_key="demo-send-1")
    assert sent.status == "SENT"
    assert sent.provider == "mock"
    assert sent.provider_message_id.startswith("mock-email-")
    assert sent.thread_id.startswith("mock-thread-")
    assert sent.idempotency_key == "demo-send-1"
    assert lead.status == "CONTACTED"


def test_approved_email_cannot_be_edited(session):
    tenant, lead, approver = create_email_fixture(session)
    service = EmailService(session, tenant.id, MockEmailProvider())
    draft = service.generate_demo_draft(lead.id)
    service.submit_for_approval(draft.id)
    service.approve(draft.id, approver.id)

    try:
        service.update_draft(
            draft.id,
            EmailDraftUpdate(subject="Changed after approval", body="Changed"),
        )
    except EmailWorkflowError:
        pass
    else:
        raise AssertionError("Approved email was editable")
