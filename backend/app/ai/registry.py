import os
import sys
import pkgutil
import importlib
import inspect
import logging
from typing import Dict, List, Optional, Type

from app.ai.providers.base.provider import LLMProvider

logger = logging.getLogger(__name__)

PROVIDERS_PACKAGE = "app.ai.providers"
SKIP_MODULES = {"base", "openai_compatible", "__pycache__"}


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._auto_discovered = False

    async def discover(self) -> None:
        if self._auto_discovered:
            return
        self._auto_discovered = True
        package = importlib.import_module(PROVIDERS_PACKAGE)
        package_path = os.path.dirname(package.__file__)

        for entry in os.scandir(package_path):
            if not entry.is_dir() or entry.name in SKIP_MODULES or entry.name.startswith("_"):
                continue
            try:
                provider_module = importlib.import_module(f"{PROVIDERS_PACKAGE}.{entry.name}")
                for attr_name in dir(provider_module):
                    attr = getattr(provider_module, attr_name)
                    if (inspect.isclass(attr) and issubclass(attr, LLMProvider) and
                            attr is not LLMProvider and not inspect.isabstract(attr)):
                        instance = attr()
                        await instance.initialize()
                        self._providers[instance.name] = instance
                        logger.info(f"Auto-discovered LLM provider: {instance.name}")
            except Exception as e:
                logger.warning(f"Failed to load provider '{entry.name}': {e}")

    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)

    def get_all(self) -> Dict[str, LLMProvider]:
        return dict(self._providers)

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider
        logger.info(f"Registered LLM provider: {provider.name}")

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)
        logger.info(f"Unregistered LLM provider: {name}")


provider_registry = ProviderRegistry()
