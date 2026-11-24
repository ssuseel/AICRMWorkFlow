"""Shared Streamlit styling."""

import streamlit as st

ENTERPRISE_CSS = """
<style>
:root {
    --brand-primary: #6558D3;
    --brand-primary-hover: #5145BE;
    --brand-teal: #167C80;
    --surface-main: #F8F7FC;
    --surface-card: #FFFFFF;
    --surface-tint: #F1EFF9;
    --text-primary: #211D35;
    --text-muted: #6E687E;
    --border-subtle: #E7E3F0;
    --border-control: #898396;
}
.block-container {
    max-width: 1320px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
[data-testid="stAppViewContainer"] {
    background: var(--surface-main);
    color: var(--text-primary);
}
[data-testid="stSidebar"] {
    background: var(--surface-tint);
    border-right: 1px solid var(--border-subtle);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--text-muted);
}
[data-testid="stMetric"] {
    background: var(--surface-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 3px 12px rgba(48, 37, 91, 0.045);
    transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}
[data-testid="stMetric"]:hover {
    border-color: #CFC8EF;
    box-shadow: 0 7px 20px rgba(48, 37, 91, 0.08);
    transform: translateY(-1px);
}
[data-testid="stMetricLabel"] {
    color: var(--text-muted);
}
[data-testid="stMetricValue"] {
    color: var(--text-primary);
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [role="combobox"] {
    border-color: var(--border-control);
}
.phase-banner {
    background: linear-gradient(110deg, #F0EDFF 0%, #F1FAF8 100%);
    border: 1px solid #E8E3F4;
    border-left: 4px solid var(--brand-primary);
    border-radius: 12px;
    color: var(--text-primary);
    padding: 0.85rem 1rem;
}
div.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: var(--brand-primary);
    border-color: var(--brand-primary);
    border-radius: 10px;
    color: #FFFFFF;
    transition: background-color 140ms ease, border-color 140ms ease;
}
div.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: var(--brand-primary-hover);
    border-color: var(--brand-primary-hover);
    color: #FFFFFF;
}
div.stButton > button:focus-visible,
[data-testid="stBaseButton"]:focus-visible,
a:focus-visible {
    outline: 3px solid var(--brand-primary);
    outline-offset: 2px;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stSelectbox"] [role="combobox"]:focus {
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 1px var(--brand-primary);
}
a {
    color: var(--brand-teal);
}
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        scroll-behavior: auto !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
"""


def apply_styles() -> None:
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)
