"""Follow-up and response intelligence Streamlit page."""

from datetime import UTC, datetime, timedelta

import streamlit as st

from src.db.models import EmailResponse
from src.db.session import SessionLocal
from src.domain.schemas import FollowUpCreate, IncomingEmail
from src.repositories.lead_repository import LeadRepository
from src.services.follow_up_service import FollowUpService
from src.services.response_intelligence_service import ResponseIntelligenceService
from src.ui.styles import apply_styles


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("Responses and Follow-ups")
    tab_responses, tab_followups = st.tabs(["Response review", "Follow-up queue"])

    with SessionLocal() as session:
        response_service = ResponseIntelligenceService(session, tenant_id)
        follow_service = FollowUpService(session, tenant_id)

        with tab_responses:
            st.subheader("Incoming response intake")
            st.caption(
                "Manual demonstration intake. Initial release never sends automatic replies."
            )
            with st.form("response_intake"):
                from_address = st.text_input("From", "customer@example.com")
                subject = st.text_input("Subject", "Interested in a demo")
                body = st.text_area(
                    "Message",
                    "We are interested. Could you share more details and schedule a call?",
                )
                provider_message_id = st.text_input(
                    "Provider message ID",
                    f"demo-response-{datetime.now(UTC).timestamp():.0f}",
                )
                thread_id = st.text_input("Thread ID", "demo-thread")
                submitted = st.form_submit_button("Classify response")
                if submitted:
                    response = response_service.ingest(
                        IncomingEmail(
                            provider_message_id=provider_message_id,
                            thread_id=thread_id,
                            from_address=from_address,
                            to_address="sender@example.com",
                            subject=subject,
                            body=body,
                        )
                    )
                    st.success(
                        f"Classification: {response.classification} "
                        f"(priority: {response.priority})"
                    )
                    st.write(response.summary)
                    st.write(f"**Recommended action:** {response.recommended_action}")

            st.divider()
            responses = (
                session.query(EmailResponse)
                .filter(EmailResponse.tenant_id == tenant_id)
                .order_by(EmailResponse.created_at.desc())
                .all()
            )
            if not responses:
                st.info("No responses have been received.")
            for response in responses:
                with st.expander(
                    f"{response.classification} — {response.priority}",
                    expanded=response.human_review_required,
                ):
                    st.write(response.summary)
                    st.write(f"Intent: {response.customer_intent or 'Unknown'}")
                    st.write(
                        f"Recommended action: {response.recommended_action or 'Review'}"
                    )
                    st.write(
                        "Human review required"
                        if response.human_review_required
                        else "No immediate human review required"
                    )

        with tab_followups:
            follow_service.mark_overdue()
            st.subheader("Persistent follow-up queue")
            lead_repository = LeadRepository(session, tenant_id)
            leads = lead_repository.list_active()
            lead_options = {
                f"{lead.first_name} {lead.last_name} — {lead.email}": lead
                for lead in leads
            }
            if lead_options:
                selected_label = st.selectbox("Lead", list(lead_options))
                selected = lead_options[selected_label]
                title = st.text_input("Follow-up title", "Discovery follow-up")
                priority = st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    index=1,
                )
                due = st.date_input(
                    "Due date",
                    value=datetime.now(UTC).date() + timedelta(days=3),
                )
                if st.button("Schedule follow-up"):
                    due_at = datetime.combine(due, datetime.min.time()).replace(
                        tzinfo=UTC
                    )
                    follow_service.create(
                        FollowUpCreate(
                            lead_id=selected.id,
                            title=title,
                            priority=priority,
                            due_at=due_at,
                        )
                    )
                    st.success("Follow-up scheduled.")
                    st.rerun()

            st.divider()
            followups = follow_service.list_all()
            if not followups:
                st.info("No follow-ups scheduled.")
            for follow_up in followups:
                lead = next(
                    (lead for lead in leads if lead.id == follow_up.lead_id),
                    None,
                )
                lead_name = (
                    f"{lead.first_name} {lead.last_name}" if lead else "Unknown lead"
                )
                with st.expander(
                    f"{follow_up.title} — {follow_up.status}",
                    expanded=follow_up.status in {"SCHEDULED", "OVERDUE"},
                ):
                    st.write(f"Lead: {lead_name}")
                    st.write(f"Due: {follow_up.due_at}")
                    st.write(f"Priority: {follow_up.priority}")
                    if follow_up.status not in {"COMPLETED", "CANCELLED"}:
                        if st.button(
                            "Complete",
                            key=f"complete_{follow_up.id}",
                        ):
                            follow_service.complete(follow_up.id)
                            st.rerun()
                        if st.button(
                            "Cancel",
                            key=f"cancel_{follow_up.id}",
                        ):
                            follow_service.cancel(
                                follow_up.id,
                                "Cancelled manually",
                            )
                            st.rerun()
