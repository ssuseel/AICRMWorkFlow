"""Email provider selection tests."""

from src.config.settings import Settings
from src.integrations.email.base import EmailPermanentError
from src.integrations.email.factory import create_email_provider
from src.integrations.email.mock_provider import MockEmailProvider


def test_mock_provider_is_default(monkeypatch):
    settings = Settings(email_provider="mock")
    monkeypatch.setattr(
        "src.integrations.email.factory.get_settings",
        lambda: settings,
    )
    assert isinstance(create_email_provider(), MockEmailProvider)


def test_gmail_provider_requires_credentials(monkeypatch):
    settings = Settings(
        email_provider="gmail",
        gmail_client_id="",
        gmail_client_secret="",
        gmail_refresh_token="",
        gmail_sender="",
    )
    monkeypatch.setattr(
        "src.integrations.email.factory.get_settings",
        lambda: settings,
    )
    try:
        create_email_provider()
    except EmailPermanentError as exc:
        assert "Gmail requires" in str(exc)
    else:
        raise AssertionError("Gmail provider accepted missing credentials")
