"""Environment and Streamlit configuration."""

from functools import lru_cache
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_url: str = Field(default="sqlite:///./aicrm.db")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    default_tenant_id: UUID = Field(
        default=UUID("00000000-0000-0000-0000-000000000001")
    )
    ai_provider: str = Field(default="mock")
    email_provider: str = Field(default="mock")
    crm_provider: str = Field(default="mock")
    gmail_client_id: str = Field(default="")
    gmail_client_secret: str = Field(default="")
    gmail_refresh_token: str = Field(default="")
    gmail_sender: str = Field(default="")
    salesforce_client_id: str = Field(default="")
    salesforce_client_secret: str = Field(default="")
    salesforce_login_url: str = Field(default="https://login.salesforce.com")
    salesforce_api_version: str = Field(default="v60.0")


@lru_cache
def get_settings() -> Settings:
    import os

    try:
        import streamlit as st
        from streamlit.errors import StreamlitSecretNotFoundError

        try:
            secrets = dict(st.secrets)
        except StreamlitSecretNotFoundError:
            secrets = {}
    except ImportError:
        secrets = {}

    def value(name: str, default: str) -> str:
        return str(secrets.get(name, os.getenv(name.upper(), default)))

    return Settings(
        database_url=value("DATABASE_URL", "sqlite:///./aicrm.db"),
        app_env=value("APP_ENV", "development"),
        log_level=value("LOG_LEVEL", "INFO").upper(),
        default_tenant_id=UUID(
            value(
                "DEFAULT_TENANT_ID",
                "00000000-0000-0000-0000-000000000001",
            )
        ),
        ai_provider=value("AI_PROVIDER", "mock"),
        email_provider=value("EMAIL_PROVIDER", "mock"),
        crm_provider=value("CRM_PROVIDER", "mock"),
        gmail_client_id=value("GMAIL_CLIENT_ID", ""),
        gmail_client_secret=value("GMAIL_CLIENT_SECRET", ""),
        gmail_refresh_token=value("GMAIL_REFRESH_TOKEN", ""),
        gmail_sender=value("GMAIL_SENDER", ""),
        salesforce_client_id=value("SALESFORCE_CLIENT_ID", ""),
        salesforce_client_secret=value("SALESFORCE_CLIENT_SECRET", ""),
        salesforce_login_url=value(
            "SALESFORCE_LOGIN_URL", "https://login.salesforce.com"
        ),
        salesforce_api_version=value("SALESFORCE_API_VERSION", "v60.0"),
    )
