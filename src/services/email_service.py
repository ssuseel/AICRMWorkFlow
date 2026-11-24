"""Draft, approval, preview and mock-send email service."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.models import Email, Lead
from src.domain.enums import EmailStatus
from src.domain.schemas import DeliveryResult, EmailDraftCreate, EmailDraftUpdate
from src.integrations.email.base import (
    EmailPermanentError,
    EmailProvider,
    EmailTransientError,
)
from src.integrations.email.factory import create_email_provider


class EmailWorkflowError(ValueError):
    pass


class EmailApprovalRequiredError(EmailWorkflowError):
    pass


class EmailService:
    def __init__(
        self,
        session: Session,
        tenant_id: str,
        provider: EmailProvider | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.provider = provider or create_email_provider()

    def _get_email(self, email_id: str) -> Email:
        email = (
            self.session.query(Email)
            .filter(
                Email.tenant_id == self.tenant_id,
                Email.id == email_id,
            )
            .first()
        )
        if email is None:
            raise LookupError("Email not found")
        return email

    def _get_lead(self, lead_id: str) -> Lead:
        lead = (
            self.session.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
            .first()
        )
        if lead is None:
            raise LookupError("Lead not found")
        return lead

    def create_draft(self, data: EmailDraftCreate) -> Email:
        lead = self._get_lead(str(data.lead_id))
        email = Email(
            tenant_id=self.tenant_id,
            lead_id=lead.id,
            subject=data.subject.strip(),
            body=data.body.strip(),
            status=EmailStatus.DRAFT.value,
            provider="mock",
        )
        self.session.add(email)
        self.session.commit()
        self.session.refresh(email)
        return email

    def generate_demo_draft(self, lead_id: str) -> Email:
        lead = self._get_lead(lead_id)
        subject = f"{lead.company or 'Your team'} and workflow automation"
        body = (
            f"Hi {lead.first_name},\n\n"
            f"I saw your team at {lead.company or 'your organization'} may be "
            "interested in improving customer workflows. I would welcome a brief "
            "conversation to understand your priorities and identify a practical "
            "next step.\n\n"
            "Would you be open to a 20-minute discovery call?\n\n"
            "Best regards"
        )
        return self.create_draft(
            EmailDraftCreate(lead_id=lead.id, subject=subject, body=body)
        )

    def update_draft(self, email_id: str, data: EmailDraftUpdate) -> Email:
        email = self._get_email(email_id)
        if email.status != EmailStatus.DRAFT.value:
            raise EmailWorkflowError("Only draft emails can be edited")
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(email, field, value.strip())
        self.session.commit()
        self.session.refresh(email)
        return email

    def preview(self, email_id: str) -> dict[str, str]:
        email = self._get_email(email_id)
        lead = self._get_lead(email.lead_id)
        return {
            "to": lead.email,
            "subject": email.subject,
            "body": email.body,
        }

    def submit_for_approval(self, email_id: str) -> Email:
        email = self._get_email(email_id)
        if email.status != EmailStatus.DRAFT.value:
            raise EmailWorkflowError("Only draft emails can be submitted")
        email.status = EmailStatus.PENDING_APPROVAL.value
        self.session.commit()
        self.session.refresh(email)
        return email

    def approve(self, email_id: str, approver_id: str) -> Email:
        email = self._get_email(email_id)
        if email.status != EmailStatus.PENDING_APPROVAL.value:
            raise EmailWorkflowError("Email must be pending approval")
        email.status = EmailStatus.APPROVED.value
        email.approved_by_id = approver_id
        email.approved_at = datetime.now(UTC)
        email.approved_subject = email.subject
        email.approved_body = email.body
        self.session.commit()
        self.session.refresh(email)
        return email

    def send(self, email_id: str, idempotency_key: str | None = None) -> Email:
        email = self._get_email(email_id)
        if email.status != EmailStatus.APPROVED.value:
            raise EmailApprovalRequiredError(
                "Email sending requires explicit human approval"
            )
        lead = self._get_lead(email.lead_id)
        email.status = EmailStatus.SENDING.value
        email.idempotency_key = idempotency_key or f"email-send-{uuid4()}"
        self.session.commit()

        try:
            result: DeliveryResult = self.provider.send(
                lead.email,
                email.approved_subject or email.subject,
                email.approved_body or email.body,
            )
        except EmailTransientError:
            email.status = EmailStatus.DELIVERY_FAILED.value
            email.sent_at = None
            self.session.commit()
            raise
        except EmailPermanentError:
            email.status = EmailStatus.DELIVERY_FAILED.value
            email.sent_at = None
            self.session.commit()
            raise
        email.provider = result.provider
        email.provider_message_id = result.provider_message_id
        email.thread_id = result.thread_id
        email.sent_at = datetime.now(UTC)
        email.status = result.status
        lead.status = "CONTACTED"
        self.session.commit()
        self.session.refresh(email)
        return email

    def list_for_lead(self, lead_id: str) -> list[Email]:
        return list(
            self.session.query(Email)
            .filter(
                Email.tenant_id == self.tenant_id,
                Email.lead_id == lead_id,
            )
            .order_by(Email.created_at.desc())
            .all()
        )
