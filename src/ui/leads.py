"""Lead management Streamlit page."""

import math
from uuid import UUID

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from src.db.models import User
from src.db.session import SessionLocal
from src.domain.enums import LeadStatus
from src.domain.schemas import LeadCreate, LeadUpdate
from src.repositories.lead_repository import LeadRepository
from src.services.lead_service import (
    DuplicateLeadError,
    LeadDeleteRestrictedError,
    LeadService,
)
from src.services.qualification_service import QualificationService
from src.ui.styles import apply_styles


def _owners(session, tenant_id: str) -> dict[str, str]:
    users = (
        session.query(User)
        .filter(User.tenant_id == tenant_id, User.status == "active")
        .order_by(User.display_name)
        .all()
    )
    return {user.display_name: user.id for user in users}


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("Lead Management")
    tab_list, tab_create, tab_import = st.tabs(
        ["All leads", "Create lead", "CSV import"]
    )

    with SessionLocal() as session:
        repository = LeadRepository(session, tenant_id)
        service = LeadService(session, tenant_id)
        owner_map = _owners(session, tenant_id)
        with tab_list:
            st.subheader("Search and filters")
            left, right = st.columns([2, 1])
            with left:
                query = st.text_input("Search", placeholder="Name, email, or company")
            with right:
                page_size = st.selectbox("Rows per page", [10, 20, 50, 100], index=1)

            filter_a, filter_b, filter_c = st.columns(3)
            leads = repository.list_active()
            sources = sorted({lead.source for lead in leads if lead.source})
            industries = sorted({lead.industry for lead in leads if lead.industry})
            with filter_a:
                source = st.selectbox("Lead source", ["All"] + sources)
                industry = st.selectbox("Industry", ["All"] + industries)
                company = st.text_input("Company")
            with filter_b:
                status = st.selectbox(
                    "Lead status", ["All"] + [item.value for item in LeadStatus]
                )
                owner_name = st.selectbox("Lead owner", ["All"] + list(owner_map))
            with filter_c:
                min_score, max_score = st.slider(
                    "Qualification score", 0, 100, (0, 100)
                )
                sort_label = st.selectbox(
                    "Sort",
                    [
                        "Newest",
                        "Oldest",
                        "Name",
                        "Company",
                        "Highest score",
                        "Status",
                        "Next follow-up",
                    ],
                )

            date_a, date_b = st.columns(2)
            with date_a:
                created_range = st.date_input(
                    "Creation date",
                    value=None,
                )
            with date_b:
                followup_range = st.date_input(
                    "Next follow-up date",
                    value=None,
                )

            def range_parts(value):
                if isinstance(value, tuple) and len(value) == 2:
                    return value[0], value[1]
                if isinstance(value, tuple):
                    return value[0], None
                if value:
                    return value, value
                return None, None

            created_from, created_to = range_parts(created_range)
            followup_from, followup_to = range_parts(followup_range)
            sort_map = {
                "Newest": ("created_at", "desc"),
                "Oldest": ("created_at", "asc"),
                "Name": ("name", "asc"),
                "Company": ("company", "asc"),
                "Highest score": ("score", "desc"),
                "Status": ("status", "asc"),
                "Next follow-up": ("next_follow_up", "asc"),
            }
            sort, direction = sort_map[sort_label]
            page = st.session_state.setdefault("lead_page", 1)
            owner_id = None if owner_name == "All" else owner_map.get(owner_name)
            rows, total = repository.search(
                query=query,
                source=None if source == "All" else source,
                industry=None if industry == "All" else industry,
                company=company or None,
                owner_id=owner_id,
                status=None if status == "All" else status,
                min_score=min_score,
                max_score=max_score,
                created_from=created_from,
                created_to=created_to,
                next_follow_up_from=followup_from,
                next_follow_up_to=followup_to,
                sort=sort,
                direction=direction,
                page=page,
                page_size=page_size,
            )

            max_page = max(1, math.ceil(total / page_size))
            st.caption(f"{total} lead(s)")
            if rows:
                table = pd.DataFrame(
                    [
                        {
                            "Lead": f"{lead.first_name} {lead.last_name}",
                            "Email": lead.email,
                            "Company": lead.company or "",
                            "Industry": lead.industry or "",
                            "Source": lead.source,
                            "Owner": next(
                                (
                                    name
                                    for name, user_id in owner_map.items()
                                    if user_id == lead.owner_id
                                ),
                                "Unassigned",
                            ),
                            "Score": lead.qualification_score,
                            "Status": lead.status,
                            "Next follow-up": lead.next_follow_up_at,
                            "ID": lead.id,
                        }
                        for lead in rows
                    ]
                )
                st.dataframe(table, use_container_width=True, hide_index=True)
            else:
                st.info("No leads match the selected filters.")

            previous, page_label, next_page = st.columns([1, 3, 1])
            with previous:
                if st.button("Previous", disabled=page <= 1):
                    st.session_state.lead_page = max(1, page - 1)
                    st.rerun()
            with page_label:
                st.write(f"Page {page} of {max_page}")
            with next_page:
                if st.button("Next", disabled=page >= max_page):
                    st.session_state.lead_page = min(max_page, page + 1)
                    st.rerun()

            st.divider()
            lead_options = {
                f"{lead.first_name} {lead.last_name} — {lead.email}": lead
                for lead in rows
            }
            if lead_options:
                selected_label = st.selectbox("Edit or delete lead", list(lead_options))
                selected = lead_options[selected_label]
                if st.button("Run AI qualification", key=f"qualify_{selected.id}"):
                    try:
                        result = QualificationService(
                            session,
                            tenant_id,
                        ).qualify(selected.id)
                        st.success(
                            f"Qualification complete: score {result.score}, "
                            f"status {result.status}"
                        )
                        st.write(result.evidence.summary)
                        evidence = result.evidence
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Supporting evidence**")
                            st.json(evidence.evidence)
                        with c2:
                            st.write("**Missing information**")
                            st.write(
                                evidence.missing_information or ["None identified"]
                            )
                        st.write("**Recommended actions**")
                        for action in evidence.recommended_actions:
                            st.write(f"- {action}")
                        st.rerun()
                    except (LookupError, RuntimeError, TimeoutError) as exc:
                        st.error(f"Unable to qualify lead: {exc}")
                with st.form("edit_lead"):
                    edit_first = st.text_input("First name", selected.first_name)
                    edit_last = st.text_input("Last name", selected.last_name)
                    edit_email = st.text_input("Email", selected.email)
                    edit_company = st.text_input("Company", selected.company or "")
                    edit_industry = st.text_input("Industry", selected.industry or "")
                    edit_source = st.text_input("Source", selected.source)
                    edit_status = st.selectbox(
                        "Status",
                        [item.value for item in LeadStatus],
                        index=[item.value for item in LeadStatus].index(
                            selected.status
                        ),
                    )
                    edit_score = st.slider(
                        "Qualification score",
                        0,
                        100,
                        int(selected.qualification_score),
                        key="edit_score",
                    )
                    edit_owner_name = next(
                        (
                            name
                            for name, user_id in owner_map.items()
                            if user_id == selected.owner_id
                        ),
                        "Unassigned",
                    )
                    edit_owner_name = st.selectbox(
                        "Owner",
                        ["Unassigned"] + list(owner_map),
                        index=(["Unassigned"] + list(owner_map)).index(edit_owner_name),
                    )
                    submitted_edit = st.form_submit_button("Save changes")
                    if submitted_edit:
                        try:
                            owner_id_value = (
                                None
                                if edit_owner_name == "Unassigned"
                                else UUID(owner_map[edit_owner_name])
                            )
                            service.update(
                                selected.id,
                                LeadUpdate(
                                    first_name=edit_first,
                                    last_name=edit_last,
                                    email=edit_email,
                                    company=edit_company or None,
                                    industry=edit_industry or None,
                                    source=edit_source,
                                    status=edit_status,
                                    qualification_score=edit_score,
                                    owner_id=owner_id_value,
                                ),
                            )
                            st.success("Lead updated.")
                            st.rerun()
                        except DuplicateLeadError as exc:
                            st.error(str(exc))
                        except (LookupError, ValidationError, ValueError) as exc:
                            st.error(f"Unable to update lead: {exc}")
                if st.button("Delete selected lead", type="secondary"):
                    try:
                        service.soft_delete(selected.id)
                        st.success("Lead deleted.")
                        st.rerun()
                    except LeadDeleteRestrictedError as exc:
                        st.error(str(exc))

        with tab_create:
            st.subheader("Create lead")
            with st.form("create_lead"):
                first_name = st.text_input("First name")
                last_name = st.text_input("Last name")
                email = st.text_input("Email")
                company = st.text_input("Company")
                title = st.text_input("Job title")
                industry = st.text_input("Industry")
                source = st.text_input("Lead source", "Manual")
                owner_name = st.selectbox(
                    "Lead owner", ["Unassigned"] + list(owner_map)
                )
                submitted = st.form_submit_button("Create lead")
                if submitted:
                    try:
                        service.create(
                            LeadCreate(
                                first_name=first_name,
                                last_name=last_name,
                                email=email,
                                company=company or None,
                                title=title or None,
                                industry=industry or None,
                                source=source,
                                owner_id=(
                                    UUID(owner_map[owner_name])
                                    if owner_name != "Unassigned"
                                    else None
                                ),
                            )
                        )
                        st.success("Lead created.")
                        st.rerun()
                    except DuplicateLeadError as exc:
                        st.error(str(exc))
                    except (LookupError, ValidationError, ValueError) as exc:
                        st.error(f"Unable to create lead: {exc}")

        with tab_import:
            st.subheader("Import leads from CSV")
            st.caption("Required columns: first_name, last_name, email")
            uploaded = st.file_uploader("CSV file", type=["csv"])
            if uploaded and st.button("Import CSV"):
                counts = service.import_csv(uploaded.getvalue().decode("utf-8-sig"))
                st.metric("Created", counts["created"])
                st.metric("Duplicates", counts["duplicates"])
                st.metric("Rejected", counts["rejected"])
