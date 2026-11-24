"""Analytics dashboard."""

import pandas as pd
import streamlit as st

from src.db.models import Lead, User
from src.db.session import SessionLocal
from src.domain.analytics import AnalyticsFilters
from src.services.analytics_service import AnalyticsService
from src.ui.styles import apply_styles


def _percentage(value: float) -> str:
    return f"{value:.1%}"


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("Analytics")
    st.caption("Live tenant-scoped metrics calculated from persisted workflow data.")

    with SessionLocal() as session:
        leads = (
            session.query(Lead)
            .filter(
                Lead.tenant_id == tenant_id,
                Lead.deleted_at.is_(None),
            )
            .all()
        )
        owners = (
            session.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.status == "active",
            )
            .order_by(User.display_name)
            .all()
        )
        sources = sorted({lead.source for lead in leads if lead.source})
        industries = sorted({lead.industry for lead in leads if lead.industry})
        statuses = sorted({lead.status for lead in leads if lead.status})

        with st.expander("Analytics filters", expanded=True):
            date_column, owner_column = st.columns(2)
            with date_column:
                date_range = st.date_input("Date range", value=())
            with owner_column:
                owner_options = {"All owners": None} | {
                    owner.display_name: owner.id for owner in owners
                }
                selected_owner = st.selectbox("Owner", list(owner_options))
            industry_column, source_column, status_column = st.columns(3)
            with industry_column:
                industry = st.selectbox("Industry", ["All industries"] + industries)
            with source_column:
                source = st.selectbox("Lead source", ["All sources"] + sources)
            with status_column:
                status = st.selectbox("Lead status", ["All statuses"] + statuses)

        start_date = end_date = None
        if isinstance(date_range, tuple):
            if len(date_range) == 1:
                start_date = end_date = date_range[0]
            elif len(date_range) == 2:
                start_date, end_date = date_range
        filters = AnalyticsFilters(
            start_date=start_date,
            end_date=end_date,
            owner_id=owner_options[selected_owner],
            industry=None if industry == "All industries" else industry,
            source=None if source == "All sources" else source,
            status=None if status == "All statuses" else status,
        )
        analytics = AnalyticsService(session, tenant_id).summary(filters)

    conversion = analytics["conversion"]
    email = analytics["email"]
    followups = analytics["follow_ups"]
    st.subheader("Lifecycle performance")
    metrics = st.columns(5)
    metrics[0].metric("Leads", conversion["leads"])
    metrics[1].metric(
        "Lead-to-customer",
        _percentage(conversion["conversion_rate"]),
        f"{conversion['customers']} customers",
    )
    metrics[2].metric(
        "Email delivery rate",
        _percentage(email["delivery_rate"]),
        f"{email['sent']} sent / {email['attempted']} attempts",
    )
    metrics[3].metric(
        "Email response rate",
        _percentage(email["response_rate"]),
        f"{email['responses']} responses",
    )
    metrics[4].metric(
        "Follow-up completion",
        _percentage(followups["completion_rate"]),
        f"{followups['completed']} completed / {followups['total']} total",
    )

    left, right = st.columns(2)
    with left:
        st.subheader("Lead acquisition trend")
        trends = analytics["acquisition_trends"]
        if trends:
            frame = pd.DataFrame(trends).set_index("date")
            st.line_chart(frame["leads"])
        else:
            st.info("No leads match the selected date and filters.")
    with right:
        st.subheader("Qualification distribution")
        distribution = analytics["qualification_distribution"]
        if distribution:
            st.bar_chart(pd.DataFrame(distribution).set_index("score_band"))
        else:
            st.info("No qualification scores are available for this selection.")

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.subheader("Pipeline activity")
        pipeline = analytics["pipeline"]
        if pipeline:
            st.bar_chart(pd.DataFrame(pipeline).set_index("status"))
        else:
            st.info("No pipeline activity for this selection.")
        st.subheader("Follow-up effectiveness")
        st.metric("Overdue follow-ups", followups["overdue"])
        st.metric("Customers with completed follow-ups", followups["converted_leads"])

    with lower_right:
        st.subheader("CRM synchronization health")
        crm_health = analytics["crm_health"]
        if crm_health:
            st.dataframe(
                pd.DataFrame(crm_health),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No CRM synchronization activity for this selection.")
        st.subheader("Team productivity")
        productivity = analytics["team_productivity"]
        if productivity:
            st.dataframe(
                pd.DataFrame(productivity),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No team activity for this selection.")
