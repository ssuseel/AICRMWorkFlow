"""CRM provider factory."""

from src.config.settings import get_settings
from src.integrations.crm.base import CRMPermanentError, CRMProvider
from src.integrations.crm.mock_provider import MockCRMProvider
from src.integrations.crm.salesforce_provider import SalesforceProvider


def create_crm_provider(provider_name: str | None = None) -> CRMProvider:
    settings = get_settings()
    name = (provider_name or settings.crm_provider).lower()
    if name == "mock":
        return MockCRMProvider()
    if name == "salesforce":
        return SalesforceProvider(
            client_id=settings.salesforce_client_id,
            client_secret=settings.salesforce_client_secret,
            login_url=settings.salesforce_login_url,
            api_version=settings.salesforce_api_version,
        )
    raise CRMPermanentError(f"Unsupported CRM provider: {name}")
