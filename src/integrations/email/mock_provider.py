"""Clearly labelled mock email provider."""

from uuid import uuid4

from src.domain.schemas import DeliveryResult
from src.integrations.email.base import EmailProvider


class MockEmailProvider(EmailProvider):
    def send(self, recipient: str, subject: str, body: str) -> DeliveryResult:
        del recipient, subject, body
        message_id = f"mock-email-{uuid4()}"
        return DeliveryResult(
            provider="mock",
            provider_message_id=message_id,
            thread_id=f"mock-thread-{uuid4()}",
            status="SENT",
        )
