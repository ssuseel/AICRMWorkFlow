"""AI provider factory."""

from src.integrations.ai.base import AIProvider
from src.integrations.ai.mock_provider import MockAIProvider


def create_ai_provider(provider_name: str = "mock") -> AIProvider:
    if provider_name.lower() == "mock":
        return MockAIProvider()
    return MockAIProvider()
