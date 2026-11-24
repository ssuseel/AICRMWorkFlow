"""Email provider interface."""

from abc import ABC, abstractmethod

from src.domain.schemas import DeliveryResult


class EmailProvider(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> DeliveryResult:
        """Send an approved email and return the provider delivery result."""
