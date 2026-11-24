"""Email provider factory."""

from src.config.settings import get_settings
from src.integrations.email.base import EmailPermanentError, EmailProvider
from src.integrations.email.gmail_provider import GmailProvider
from src.integrations.email.mock_provider import MockEmailProvider


def create_email_provider(provider_name: str | None = None) -> EmailProvider:
    settings = get_settings()
    name = (provider_name or settings.email_provider).lower()
    if name == "gmail":
        return GmailProvider(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            refresh_token=settings.gmail_refresh_token,
            sender=settings.gmail_sender,
        )
    if name == "mock":
        return MockEmailProvider()
    raise EmailPermanentError(f"Unsupported email provider: {name}")
