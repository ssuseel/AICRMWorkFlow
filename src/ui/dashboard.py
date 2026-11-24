"""Dashboard page."""

import streamlit as st

from src.db.session import SessionLocal
from src.services.dashboard_service import DashboardService
from src.ui.styles import apply_styles


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("Customer Workflow Dashboard")
    st.markdown(
        '<div class="phase-banner">Demo workspace · Phase 1 foundation</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    with SessionLocal() as session:
        metrics = DashboardService(session, tenant_id).metrics()

    cards = [
        ("Total leads", "total_leads"),
        ("New leads", "new_leads"),
        ("Qualified leads", "qualified_leads"),
        ("Emails generated", "emails_generated"),
        ("Awaiting approval", "emails_awaiting_approval"),
        ("Emails sent", "emails_sent"),
        ("Responses received", "responses_received"),
        ("Follow-ups due", "followups_due"),
        ("CRM sync pending", "crm_sync_pending"),
    ]
    for row_start in range(0, len(cards), 3):
        columns = st.columns(3)
        for column, (label, key) in zip(columns, cards[row_start : row_start + 3]):
            with column:
                st.metric(label, metrics[key])
