"""Provider-neutral CRM integration contracts."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.schemas import CRMUpsertResult


class CRMProviderError(RuntimeError):
    pass


class CRMTransientError(CRMProviderError):
    pass


class CRMPermanentError(CRMProviderError):
    pass


class CRMProvider(ABC):
    @abstractmethod
    def upsert_lead(
        self,
        lead: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        """Create or update a lead without creating duplicates."""

    @abstractmethod
    def upsert_contact(
        self,
        contact: dict[str, Any],
        field_mapping: dict[str, str],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        """Create or update a contact."""

    @abstractmethod
    def upsert_account(
        self,
        account: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        """Create or update an account."""

    @abstractmethod
    def associate_contact_account(
        self,
        contact_id: str,
        account_id: str,
    ) -> None:
        """Associate a contact with an account."""

    @abstractmethod
    def create_task(
        self,
        task: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        """Create a CRM task."""

    @abstractmethod
    def log_activity(
        self,
        activity: dict[str, Any],
        idempotency_key: str,
    ) -> CRMUpsertResult:
        """Log a CRM activity."""
