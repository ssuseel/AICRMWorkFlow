"""AICRMWorkFlow Streamlit application entry point."""

import streamlit as st

from src.config.settings import get_settings
from src.db.base import Base
from src.db.session import engine
from src.logging_config import configure_logging
from src.ui.crm import render as render_crm
from src.ui.dashboard import render
from src.ui.emails import render as render_emails
from src.ui.followups import render as render_followups
from src.ui.leads import render as render_leads

configure_logging()
st.set_page_config(
    page_title="AICRMWorkFlow",
    page_icon="A",
    layout="wide",
)

settings = get_settings()
Base.metadata.create_all(engine)


def dashboard_page() -> None:
    render(str(settings.default_tenant_id))


def leads_page() -> None:
    render_leads(str(settings.default_tenant_id))


def emails_page() -> None:
    render_emails(str(settings.default_tenant_id))


def response_followup_page() -> None:
    render_followups(str(settings.default_tenant_id))


def crm_page() -> None:
    render_crm(str(settings.default_tenant_id))


pages = {
    "Workspace": [
        st.Page(
            dashboard_page,
            title="Dashboard",
            icon=":material/dashboard:",
            url_path="dashboard",
            default=True,
        )
    ],
    "Sales": [
        st.Page(
            leads_page,
            title="Leads",
            icon=":material/contact_mail:",
            url_path="leads",
        ),
        st.Page(
            emails_page,
            title="Email Outreach",
            icon=":material/mail:",
            url_path="emails",
        ),
        st.Page(
            response_followup_page,
            title="Responses & Follow-ups",
            icon=":material/task:",
            url_path="responses-followups",
        ),
        st.Page(
            crm_page,
            title="CRM Sync",
            icon=":material/sync:",
            url_path="crm-sync",
        ),
    ],
}

navigation = st.navigation(pages)
navigation.run()
