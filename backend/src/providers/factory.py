"""Provider factory for creating provider instances."""

from enum import Enum
from typing import Optional

from .base import BaseProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .ollama import OllamaProvider


class ProviderType(str, Enum):
    """Supported provider types."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


# Provider registry
_providers: dict[ProviderType, BaseProvider] = {}


def get_provider(provider_type: ProviderType | str) -> BaseProvider:
    """
    Get or create a provider instance.

    Args:
        provider_type: The type of provider to get

    Returns:
        A provider instance

    Raises:
        ValueError: If the provider type is unknown
    """
    if isinstance(provider_type, str):
        try:
            provider_type = ProviderType(provider_type.lower())
        except ValueError:
            raise ValueError(f"Unknown provider type: {provider_type}")

    if provider_type not in _providers:
        if provider_type == ProviderType.ANTHROPIC:
            _providers[provider_type] = AnthropicProvider()
        elif provider_type == ProviderType.OPENAI:
            _providers[provider_type] = OpenAIProvider()
        elif provider_type == ProviderType.OLLAMA:
            _providers[provider_type] = OllamaProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    return _providers[provider_type]


def get_available_providers() -> list[ProviderType]:
    """Get list of configured and available providers."""
    available = []
    for provider_type in ProviderType:
        try:
            provider = get_provider(provider_type)
            if provider.is_available():
                available.append(provider_type)
        except Exception:
            pass
    return available


def get_all_models() -> dict[str, list[str]]:
    """Get all available models by provider."""
    models = {}
    for provider_type in ProviderType:
        try:
            provider = get_provider(provider_type)
            if provider.is_available():
                models[provider_type.value] = provider.available_models
        except Exception:
            pass
    return models
