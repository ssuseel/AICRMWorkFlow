"""AICRMWorkFlow Streamlit application entry point."""

import streamlit as st

from src.config.settings import get_settings
from src.db.base import Base
from src.db.session import engine
from src.logging_config import configure_logging
from src.ui.dashboard import render
from src.ui.leads import render as render_leads

configure_logging()
st.set_page_config(
    page_title="AICRMWorkFlow",
    page_icon="A",
    layout="wide",
)

settings = get_settings()
Base.metadata.create_all(engine)

pages = {
    "Workspace": [
        st.Page(
            lambda: render(str(settings.default_tenant_id)),
            title="Dashboard",
            icon=":material/dashboard:",
        )
    ],
    "Sales": [
        st.Page(
            lambda: render_leads(str(settings.default_tenant_id)),
            title="Leads",
            icon=":material/contact_mail:",
        )
    ],
}

navigation = st.navigation(pages)
navigation.run()
