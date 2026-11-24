"""Email provider interface."""

from abc import ABC, abstractmethod

from src.domain.schemas import DeliveryResult


class EmailProviderError(RuntimeError):
    pass


class EmailTransientError(EmailProviderError):
    pass


class EmailPermanentError(EmailProviderError):
    pass


class EmailProvider(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> DeliveryResult:
        """Send an approved email and return the provider delivery result."""

    def fetch_incoming(self, since: str | None = None) -> list:
        """Fetch incoming messages when supported by the provider."""
        return []

    def get_thread(self, thread_id: str) -> dict:
        """Retrieve a message thread when supported by the provider."""
        return {"id": thread_id, "messages": []}
