"""In-memory mock CRM provider for demonstrations and tests."""

from typing import Any

from src.domain.schemas import CRMUpsertResult
from src.integrations.crm.base import CRMProvider

_MOCK_RECORDS: dict[tuple[str, str], dict[str, Any]] = {}
_MOCK_IDEMPOTENCY: dict[str, str] = {}


class MockCRMProvider(CRMProvider):
    provider_name = "mock"

    def __init__(self) -> None:
        self.records = _MOCK_RECORDS
        self.idempotency = _MOCK_IDEMPOTENCY

    @classmethod
    def clear_records(cls) -> None:
        _MOCK_RECORDS.clear()
        _MOCK_IDEMPOTENCY.clear()

    def _upsert(
        self,
        entity_type: str,
        fields: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        existing_id = self.idempotency.get(idempotency_key)
        if existing_id:
            return CRMUpsertResult(
                provider=self.provider_name,
                external_id=existing_id,
                entity_type=entity_type,
                created=False,
            )
        identity = str(
            fields.get("tenant_identity")
            or fields.get("Email")
            or fields.get("email")
            or fields.get("Name")
            or fields.get("name")
            or idempotency_key
        ).lower()
        existing = self.records.get((entity_type, identity))
        external_id = (
            existing["id"]
            if existing
            else f"mock-{entity_type}-{len(self.records) + 1}"
        )
        self.records[(entity_type, identity)] = {
            "id": external_id,
            **fields,
        }
        self.idempotency[idempotency_key] = external_id
        return CRMUpsertResult(
            provider=self.provider_name,
            external_id=external_id,
            entity_type=entity_type,
            created=existing is None,
        )

    @staticmethod
    def _mapped_fields(
        values: dict[str, Any],
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        return {
            remote: values[local]
            for local, remote in field_mapping.items()
            if local in values and values[local] is not None
        }

    def upsert_lead(
        self,
        lead: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        fields = self._mapped_fields(lead, field_mapping)
        fields["tenant_identity"] = (
            f"{lead.get('tenant_id', '')}:{lead.get('email', '')}".lower()
        )
        return self._upsert(
            "lead",
            fields,
            idempotency_key,
        )

    def upsert_contact(
        self,
        contact: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert(
            "contact",
            self._mapped_fields(contact, field_mapping),
            idempotency_key,
        )

    def upsert_account(
        self,
        account: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert("account", account, idempotency_key)

    def associate_contact_account(
        self,
        contact_id: str,
        account_id: str,
    ) -> None:
        for (entity_type, _), record in self.records.items():
            if entity_type == "contact" and record["id"] == contact_id:
                record["AccountId"] = account_id
                return
        raise ValueError("Mock CRM contact was not found")

    def create_task(
        self,
        task: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert("task", task, idempotency_key)

    def log_activity(
        self,
        activity: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        return self._upsert("activity", activity, idempotency_key)
