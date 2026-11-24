"""CRM synchronization workspace."""

import streamlit as st

from src.config.settings import get_settings
from src.db.models import CRMSyncRecord
from src.db.session import SessionLocal
from src.integrations.crm.base import CRMProviderError
from src.repositories.lead_repository import LeadRepository
from src.services.crm_service import CRMService
from src.ui.styles import apply_styles


def render(tenant_id: str) -> None:
    apply_styles()
    st.title("CRM Synchronization")
    provider_name = get_settings().crm_provider.lower()
    st.caption(f"Configured provider: {provider_name}")
    if provider_name == "mock":
        st.info(
            "Mock CRM mode: records remain in this app process and are not sent externally."
        )
    elif provider_name == "salesforce":
        st.warning("Salesforce synchronization changes external Salesforce records.")

    with SessionLocal() as session:
        leads = LeadRepository(session, tenant_id).list_active()
        if not leads:
            st.info("Create leads before synchronizing with a CRM.")
            return
        lead_options = {
            f"{lead.first_name} {lead.last_name} — {lead.email}": lead.id
            for lead in leads
        }
        selected = st.selectbox("Lead to synchronize", list(lead_options))
        if st.button("Synchronize lead", type="primary"):
            try:
                service = CRMService(
                    session,
                    tenant_id,
                    provider_name=provider_name,
                )
                record = service.sync_lead(lead_options[selected])
                if record.status == "SYNCED":
                    st.success(
                        f"Synchronized with {record.provider}; external ID: {record.external_id}"
                    )
                else:
                    st.error(
                        f"Sync status: {record.status}. "
                        f"{record.last_error or 'No provider details available.'}"
                    )
            except CRMProviderError as exc:
                st.error(f"CRM provider error: {exc}")
        if st.button("Synchronize contact and account"):
            try:
                service = CRMService(
                    session,
                    tenant_id,
                    provider_name=provider_name,
                )
                contact, account = service.sync_contact_and_account(
                    lead_options[selected]
                )
                st.success(
                    f"Contact {contact.external_id} associated with account {account.external_id}."
                )
            except (CRMProviderError, ValueError, LookupError) as exc:
                st.error(f"Unable to synchronize contact and account: {exc}")

        records = (
            session.query(CRMSyncRecord)
            .filter(CRMSyncRecord.tenant_id == tenant_id)
            .order_by(CRMSyncRecord.updated_at.desc())
            .all()
        )
        st.subheader("Synchronization history")
        if records:
            st.dataframe(
                [
                    {
                        "Lead": next(
                            (
                                f"{lead.first_name} {lead.last_name}"
                                for lead in leads
                                if lead.id == record.lead_id
                            ),
                            record.lead_id,
                        ),
                        "Provider": record.provider,
                        "Status": record.status,
                        "External ID": record.external_id or "",
                        "Attempts": record.attempt_count,
                        "Next retry": record.next_retry_at,
                        "Error": record.last_error or "",
                    }
                    for record in records
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No synchronization attempts yet.")
        if st.button("Retry due synchronizations"):
            try:
                retry_service = CRMService(
                    session,
                    tenant_id,
                    provider_name=provider_name,
                )
                count = retry_service.retry_due()
                st.success(f"Processed {count} due sync attempt(s).")
                st.rerun()
            except CRMProviderError as exc:
                st.error(f"CRM provider error: {exc}")

        st.subheader("Field mapping")
        st.caption(
            "Salesforce defaults use standard Lead fields; custom mapping overrides are tenant-scoped."
        )
        local_field = st.selectbox(
            "Local lead field",
            [
                "first_name",
                "last_name",
                "email",
                "phone",
                "company",
                "title",
                "industry",
                "source",
            ],
        )
        remote_field = st.text_input("Remote CRM API field")
        if st.button("Save field mapping"):
            try:
                mapping_service = CRMService(
                    session,
                    tenant_id,
                    provider_name=provider_name,
                )
                mapping_service.set_field_mapping(local_field, remote_field)
                st.success("Field mapping saved.")
                st.rerun()
            except (CRMProviderError, ValueError) as exc:
                st.error(f"Unable to save field mapping: {exc}")
