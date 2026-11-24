"""Configuration tests."""

from src.config.settings import Settings


def test_settings_defaults_to_demo_providers():
    settings = Settings()
    assert settings.database_url == "sqlite:///./aicrm.db"
    assert settings.ai_provider == "mock"
    assert settings.email_provider == "mock"
    assert settings.crm_provider == "mock"
    assert settings.seed_demo_data is True


def test_demo_seed_setting_accepts_cloud_secret_boolean():
    settings = Settings(seed_demo_data=True)
    assert settings.seed_demo_data is True
