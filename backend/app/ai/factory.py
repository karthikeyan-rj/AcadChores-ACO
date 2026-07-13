import logging
from typing import Dict, Any, Optional

from app.ai.providers.base.provider import LLMProvider
from app.ai.registry import provider_registry
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderFactory:
    @staticmethod
    async def discover_and_register() -> None:
        """Auto-discover providers from the providers folder."""
        await provider_registry.discover()

    @staticmethod
    def get_configured_providers() -> Dict[str, LLMProvider]:
        """Get providers sorted by priority order from settings."""
        all_providers = provider_registry.get_all()
        priority = getattr(settings, "AI_PROVIDER_PRIORITY", ["ollama"])
        ordered: Dict[str, LLMProvider] = {}
        for name in priority:
            if name in all_providers:
                ordered[name] = all_providers[name]
        for name, provider in all_providers.items():
            if name not in ordered:
                ordered[name] = provider
        return ordered


provider_factory = ProviderFactory()
