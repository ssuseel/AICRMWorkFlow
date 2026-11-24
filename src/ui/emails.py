"""Email draft, approval and mock-send workspace."""

import streamlit as st

from src.config.settings import get_settings
from src.db.models import User
from src.db.session import SessionLocal
from src.domain.schemas import EmailDraftUpdate
from src.integrations.email.base import EmailPermanentError, EmailTransientError
from src.repositories.lead_repository import LeadRepository
from src.services.email_service import (
    EmailApprovalRequiredError,
    EmailService,
    EmailWorkflowError,
)
from src.ui.styles import apply_styles


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("Email Outreach")
    settings = get_settings()
    if settings.email_provider.lower() == "gmail":
        st.caption(
            "Gmail provider configured. Real sending requires explicit approval."
        )
    else:
        st.caption("Mock provider active. No external email is sent.")

    with SessionLocal() as session:
        lead_repository = LeadRepository(session, tenant_id)
        email_service = EmailService(session, tenant_id)
        leads = lead_repository.list_active()
        lead_options = {
            f"{lead.first_name} {lead.last_name} — {lead.email}": lead for lead in leads
        }
        if not lead_options:
            st.info("Create a lead before generating an email.")
            return

        selected_label = st.selectbox("Lead", list(lead_options))
        lead = lead_options[selected_label]
        existing = email_service.list_for_lead(lead.id)

        action_a, action_b = st.columns(2)
        with action_a:
            if st.button("Generate demo draft"):
                try:
                    email_service.generate_demo_draft(lead.id)
                    st.success("Demo draft generated.")
                    st.rerun()
                except LookupError as exc:
                    st.error(str(exc))
        with action_b:
            st.caption("The demo generator is mock-safe and does not send email.")

        if not existing:
            st.info("No drafts exist for this lead.")
            return

        email_options = {
            f"{email.subject} — {email.status}": email for email in existing
        }
        email_label = st.selectbox("Email", list(email_options))
        email = email_options[email_label]

        preview = email_service.preview(email.id)
        with st.expander("Preview", expanded=True):
            st.write(f"**To:** {preview['to']}")
            st.write(f"**Subject:** {preview['subject']}")
            st.markdown(preview["body"].replace("\n", "  \n"))

        if email.status == "DRAFT":
            with st.form("edit_email"):
                subject = st.text_input("Subject", email.subject)
                body = st.text_area("Body", email.body, height=220)
                save = st.form_submit_button("Save draft")
                if save:
                    try:
                        email_service.update_draft(
                            email.id,
                            EmailDraftUpdate(subject=subject, body=body),
                        )
                        st.success("Draft saved.")
                        st.rerun()
                    except (EmailWorkflowError, LookupError, ValueError) as exc:
                        st.error(str(exc))
            if st.button("Submit for approval"):
                try:
                    email_service.submit_for_approval(email.id)
                    st.success("Submitted for approval.")
                    st.rerun()
                except EmailWorkflowError as exc:
                    st.error(str(exc))

        elif email.status == "PENDING_APPROVAL":
            approvers = (
                session.query(User)
                .filter(
                    User.tenant_id == tenant_id,
                    User.status == "active",
                )
                .order_by(User.display_name)
                .all()
            )
            approver_names = {user.display_name: user.id for user in approvers}
            approver_name = st.selectbox(
                "Approving user",
                list(approver_names) if approver_names else ["Demo Approver"],
            )
            if st.button("Approve email", type="primary"):
                approver_id = (
                    approver_names.get(approver_name)
                    if approver_names
                    else "demo-approver"
                )
                try:
                    email_service.approve(email.id, approver_id)
                    st.success("Email approved. It is now eligible for mock sending.")
                    st.rerun()
                except EmailWorkflowError as exc:
                    st.error(str(exc))

        elif email.status == "APPROVED":
            st.success("Human approval captured. The mock provider is ready.")
            provider_label = (
                "Send with Gmail"
                if get_settings().email_provider.lower() == "gmail"
                else "Send with mock provider"
            )
            if st.button(provider_label, type="primary"):
                try:
                    sent = email_service.send(email.id)
                    st.success(f"Send complete: {sent.provider_message_id}")
                    st.rerun()
                except EmailApprovalRequiredError as exc:
                    st.error(str(exc))
                except EmailTransientError as exc:
                    st.error(f"Transient delivery failure: {exc}")
                except EmailPermanentError as exc:
                    st.error(f"Delivery was rejected: {exc}")
        else:
            st.info(f"Email status: {email.status}")
