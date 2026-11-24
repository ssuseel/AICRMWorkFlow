"""Tenant-scoped CRM synchronization and retry orchestration."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.db.models import AuditEvent, CRMFieldMapping, CRMSyncRecord, Lead
from src.domain.schemas import CRMUpsertResult
from src.integrations.crm.base import (
    CRMPermanentError,
    CRMProvider,
    CRMTransientError,
)
from src.integrations.crm.factory import create_crm_provider

MAX_ATTEMPTS = 5


class CRMService:
    def __init__(
        self,
        session: Session,
        tenant_id: str,
        provider: CRMProvider | None = None,
        provider_name: str | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        configured_name = provider_name
        self.provider = provider or create_crm_provider(configured_name)
        self.provider_name = (
            configured_name or getattr(self.provider, "provider_name", "mock")
        ).lower()

    def _lead(self, lead_id: str) -> Lead:
        lead = (
            self.session.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
            .first()
        )
        if lead is None:
            raise LookupError("Lead not found")
        return lead

    def _mapping(self) -> dict[str, str]:
        mappings = (
            self.session.query(CRMFieldMapping)
            .filter(
                CRMFieldMapping.tenant_id == self.tenant_id,
                CRMFieldMapping.provider == self.provider_name,
            )
            .all()
        )
        return {mapping.local_field: mapping.remote_field for mapping in mappings}

    def set_field_mapping(self, local_field: str, remote_field: str) -> CRMFieldMapping:
        allowed_local_fields = {
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "title",
            "industry",
            "source",
        }
        local_field = local_field.strip()
        remote_field = remote_field.strip()
        if local_field not in allowed_local_fields:
            raise ValueError("Unsupported local lead field")
        if not remote_field or len(remote_field) > 100:
            raise ValueError(
                "Remote CRM field is required and must be 100 characters or fewer"
            )

        mapping = (
            self.session.query(CRMFieldMapping)
            .filter(
                CRMFieldMapping.tenant_id == self.tenant_id,
                CRMFieldMapping.provider == self.provider_name,
                CRMFieldMapping.local_field == local_field,
            )
            .first()
        )
        if mapping is None:
            mapping = CRMFieldMapping(
                tenant_id=self.tenant_id,
                provider=self.provider_name,
                local_field=local_field,
                remote_field=remote_field,
            )
            self.session.add(mapping)
        else:
            mapping.remote_field = remote_field
        self.session.commit()
        self.session.refresh(mapping)
        return mapping

    @staticmethod
    def _idempotency_key(lead: Lead, provider_name: str) -> str:
        revision = lead.updated_at.isoformat() if lead.updated_at else "new"
        value = f"{lead.tenant_id}:{provider_name}:lead:{lead.id}:{revision}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def sync_lead(self, lead_id: str) -> CRMSyncRecord:
        lead = self._lead(lead_id)
        key = self._idempotency_key(lead, self.provider_name)
        record = (
            self.session.query(CRMSyncRecord)
            .filter(
                CRMSyncRecord.tenant_id == self.tenant_id,
                CRMSyncRecord.idempotency_key == key,
            )
            .first()
        )
        if record and record.status == "SYNCED":
            return record
        if record and record.status == "PERMANENT_FAILURE":
            return record
        if record is None:
            record = CRMSyncRecord(
                tenant_id=self.tenant_id,
                lead_id=lead.id,
                provider=self.provider_name,
                entity_type="lead",
                status="PENDING",
                attempt_count=0,
                idempotency_key=key,
            )
            self.session.add(record)
            self.session.flush()

        if record.attempt_count >= MAX_ATTEMPTS:
            record.status = "PERMANENT_FAILURE"
            record.last_error = "Maximum synchronization attempts reached"
            self.session.commit()
            return record

        record.status = "IN_PROGRESS"
        record.attempt_count += 1
        record.next_retry_at = None
        self.session.commit()
        try:
            result = self.provider.upsert_lead(
                self._lead_payload(lead),
                self._mapping(),
                key,
            )
        except CRMTransientError as exc:
            self._schedule_retry(record, str(exc))
        except CRMPermanentError as exc:
            record.status = "PERMANENT_FAILURE"
            record.last_error = str(exc)
            self.session.commit()
        else:
            self._mark_synced(record, result)
        self.session.refresh(record)
        return record

    def sync_contact_and_account(
        self,
        lead_id: str,
    ) -> tuple[CRMUpsertResult, CRMUpsertResult]:
        lead = self._lead(lead_id)
        if not lead.company:
            raise CRMPermanentError(
                "A company is required to synchronize a contact and account"
            )
        key_base = self._idempotency_key(lead, self.provider_name)
        mapping = self._mapping()
        account = self.provider.upsert_account(
            {"Name": lead.company},
            f"{key_base}:account",
        )
        contact = self.provider.upsert_contact(
            self._lead_payload(lead),
            mapping,
            f"{key_base}:contact",
        )
        self.provider.associate_contact_account(
            contact.external_id,
            account.external_id,
        )
        return contact, account

    def retry_due(self) -> int:
        now = datetime.now(UTC)
        records = (
            self.session.query(CRMSyncRecord)
            .filter(
                CRMSyncRecord.tenant_id == self.tenant_id,
                CRMSyncRecord.status == "RETRY_SCHEDULED",
                CRMSyncRecord.next_retry_at <= now,
            )
            .order_by(CRMSyncRecord.next_retry_at.asc())
            .all()
        )
        lead_ids = [record.lead_id for record in records]
        for lead_id in lead_ids:
            self.sync_lead(lead_id)
        return len(lead_ids)

    def _schedule_retry(self, record: CRMSyncRecord, error: str) -> None:
        record.last_error = error
        if record.attempt_count >= MAX_ATTEMPTS:
            record.status = "PERMANENT_FAILURE"
            record.next_retry_at = None
        else:
            record.status = "RETRY_SCHEDULED"
            delay_seconds = min(60 * 2 ** (record.attempt_count - 1), 3600)
            record.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        self.session.commit()

    def _mark_synced(
        self,
        record: CRMSyncRecord,
        result: CRMUpsertResult,
    ) -> None:
        record.provider = result.provider
        record.external_id = result.external_id
        record.entity_type = result.entity_type
        record.status = "SYNCED"
        record.last_error = None
        record.next_retry_at = None
        self.session.add(
            AuditEvent(
                tenant_id=self.tenant_id,
                entity_type="lead",
                entity_id=record.lead_id,
                action="crm_sync_succeeded",
                after_state={
                    "provider": result.provider,
                    "external_id": result.external_id,
                    "entity_type": result.entity_type,
                },
            )
        )
        self.session.commit()

    @staticmethod
    def _lead_payload(lead: Lead) -> dict[str, str | None]:
        return {
            "tenant_id": lead.tenant_id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "phone": lead.phone,
            "company": lead.company,
            "title": lead.title,
            "industry": lead.industry,
            "source": lead.source,
        }
