"""Model catalogue with dynamic discovery and compatibility filtering.

Combines static definitions of well-known ACO-compatible models with
dynamic model lists from providers. Filters out embedding-only, audio,
image-only, deprecated, and otherwise unsuitable models.
"""
import logging
from typing import Dict, List, Optional, Any

from app.ai.providers.base.types import ModelInfo, ProviderCapabilities
from app.ai.providers.base.cache import model_cache
from app.ai.registry import provider_registry

logger = logging.getLogger(__name__)

# Models known to work well for ACO workflow planning.
# Pricing omitted — can be added later as optional metadata.
STATIC_CATALOGUE: Dict[str, List[Dict[str, Any]]] = {
    "ollama": [],
    "openai": [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context_length": 128000,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
        {"id": "gpt-4o", "name": "GPT-4o", "context_length": 128000,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
        {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "context_length": 1048576,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
        {"id": "gpt-4.1", "name": "GPT-4.1", "context_length": 1048576,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "context_length": 128000,
         "supports_structured_output": True, "supports_tools": True},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "context_length": 128000,
         "supports_structured_output": True, "supports_tools": True},
        {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "context_length": 32768,
         "supports_structured_output": True, "supports_tools": True},
    ],
    "mistral": [
        {"id": "mistral-small-latest", "name": "Mistral Small", "context_length": 32768,
         "supports_structured_output": True, "supports_tools": True},
        {"id": "mistral-large-latest", "name": "Mistral Large", "context_length": 128000,
         "supports_structured_output": True, "supports_tools": True},
    ],
    "openrouter": [
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context_length": 200000,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
        {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "context_length": 1048576,
         "supports_structured_output": True, "supports_vision": True, "supports_tools": True},
    ],
    "cohere": [
        {"id": "command-a-03-2025", "name": "Command A", "context_length": 128000,
         "supports_structured_output": True, "supports_tools": True},
    ],
}

# Patterns in model IDs that indicate unsuitable models for ACO
UNSUITABLE_PATTERNS = (
    "embed", "tts", "whisper", "dall-e", "image", "audio",
    "moderation", "realtime", "deprecated", "-001", "-002",
    "vision-preview", "code-davinci", "code-cushman",
)


def _is_suitable_for_aco(model_id: str) -> bool:
    """Check if a model ID is suitable for ACO workflow planning."""
    lower = model_id.lower()
    for pattern in UNSUITABLE_PATTERNS:
        if pattern in lower:
            return False
    return True


class ModelCatalogue:
    """Unified model catalogue combining static definitions with dynamic discovery."""

    async def get_models(
        self,
        provider_name: Optional[str] = None,
        include_static: bool = True,
    ) -> Dict[str, List[dict]]:
        """Get models for one or all providers.

        Returns dict mapping provider name -> list of model dicts.
        """
        providers = provider_registry.get_all()
        if not providers:
            return {}

        targets = [provider_name] if provider_name else list(providers.keys())
        result: Dict[str, List[dict]] = {}

        for name in targets:
            if name not in providers:
                continue

            static_models = []
            if include_static and name in STATIC_CATALOGUE:
                static_models = [
                    {
                        "id": m["id"],
                        "provider": name,
                        "name": m.get("name", m["id"]),
                        "context_length": m.get("context_length"),
                        "supports_structured_output": m.get("supports_structured_output", False),
                        "supports_reasoning": m.get("supports_reasoning", False),
                        "supports_vision": m.get("supports_vision", False),
                        "supports_tools": m.get("supports_tools", False),
                        "supports_embeddings": m.get("supports_embeddings", False),
                        "source": "static",
                    }
                    for m in STATIC_CATALOGUE[name]
                    if _is_suitable_for_aco(m["id"])
                ]

            dynamic_models = []
            provider = providers[name]
            if provider.capabilities.supports_model_discovery:
                try:
                    cached = await model_cache.get(name)
                    if cached:
                        raw_models = cached
                    else:
                        raw_models = await provider.list_models()
                        if raw_models:
                            await model_cache.set(name, raw_models)

                    dynamic_models = [
                        {
                            "id": m.id,
                            "provider": name,
                            "name": m.name,
                            "context_length": m.context_length,
                            "supports_structured_output": m.supports_structured_output,
                            "supports_reasoning": m.supports_reasoning,
                            "supports_vision": m.supports_vision,
                            "supports_tools": m.supports_tools,
                            "supports_embeddings": m.supports_embeddings,
                            "source": "dynamic",
                        }
                        for m in raw_models
                        if _is_suitable_for_aco(m.id)
                    ]
                except Exception as e:
                    logger.warning(f"Failed to discover models for '{name}': {e}")

            seen_ids = set()
            merged = []
            for m in static_models + dynamic_models:
                if m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    merged.append(m)
            result[name] = merged

        return result

    async def get_model_info(
        self, provider_name: str, model_id: str
    ) -> Optional[dict]:
        """Get info for a specific model."""
        all_models = await self.get_models(provider_name)
        for m in all_models.get(provider_name, []):
            if m["id"] == model_id:
                return m
        return None


model_catalogue = ModelCatalogue()
