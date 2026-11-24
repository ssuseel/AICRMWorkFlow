"""Shared Streamlit styling."""

import streamlit as st

ENTERPRISE_CSS = """
<style>
.block-container { max-width: 1280px; padding-top: 2rem; }
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.phase-banner {
    background: #EFF6FF;
    border-left: 4px solid #2563EB;
    border-radius: 6px;
    padding: 0.75rem 1rem;
}
</style>
"""


def apply_styles() -> None:
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)
