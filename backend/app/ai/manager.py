import asyncio
import time
import logging
from typing import Dict, List, Optional, AsyncIterator

from app.ai.providers.base.provider import LLMProvider
from app.ai.providers.base.types import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderHealth,
    ProviderMetrics,
    ModelInfo,
    Message,
)
from app.ai.providers.base.exceptions import ProviderError, ProviderUnavailable
from app.ai.providers.base.health import health_cache
from app.ai.providers.base.cache import model_cache
from app.ai.registry import provider_registry
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self):
        self._metrics: Dict[str, ProviderMetrics] = {}
        self._lock = asyncio.Lock()

    async def get_provider(self, preferred: Optional[str] = None) -> LLMProvider:
        all_providers = provider_registry.get_all()
        if not all_providers:
            raise ProviderUnavailable("No LLM providers registered")

        candidates = []
        if preferred and preferred in all_providers:
            candidates.append(preferred)

        priority = getattr(settings, "AI_PROVIDER_PRIORITY", ["ollama"])
        for name in priority:
            if name not in candidates and name in all_providers:
                candidates.append(name)
        for name in all_providers:
            if name not in candidates:
                candidates.append(name)

        for name in candidates:
            provider = all_providers.get(name)
            if not provider:
                continue
            cached = await health_cache.get(name)
            if cached is not None and not cached.available:
                continue
            try:
                health = await provider.health()
                await health_cache.set(name, health)
                if health.available:
                    return provider
            except Exception as e:
                logger.warning(f"Provider '{name}' health check failed: {e}")
                await health_cache.set(name, ProviderHealth(
                    available=False, provider=name, error=str(e)
                ))
                continue

        raise ProviderUnavailable("All providers are unavailable")

    async def generate(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        preferred_provider: Optional[str] = None,
    ) -> CompletionResponse:
        provider = await self.get_provider(preferred_provider)
        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        start = time.monotonic()
        try:
            response = await provider.generate(request)
            latency = (time.monotonic() - start) * 1000
            response.latency_ms = latency
            self._record_metrics(provider.name, response.model or model or "",
                                 response.tokens_input, response.tokens_output,
                                 latency, response.cost, error=False)
            return response
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self._record_metrics(provider.name, model or "",
                                 0, 0, latency, 0.0, error=True)
            raise

    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.0,
        preferred_provider: Optional[str] = None,
    ) -> AsyncIterator[str]:
        provider = await self.get_provider(preferred_provider)
        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
        )
        start = time.monotonic()
        tokens = 0
        try:
            async for token in provider.stream(request):
                tokens += 1
                yield token
            latency = (time.monotonic() - start) * 1000
            self._record_metrics(provider.name, request.model or model or "",
                                 0, tokens, latency, 0.0, error=False)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self._record_metrics(provider.name, model or "",
                                 0, tokens, latency, 0.0, error=True)
            raise

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> EmbeddingResponse:
        provider = await self.get_provider(preferred_provider)
        if not provider.capabilities.supports_embeddings:
            raise ProviderError(f"Provider '{provider.name}' does not support embeddings")
        request = EmbeddingRequest(input=text, model=model)
        start = time.monotonic()
        try:
            response = await provider.embed(request)
            response.latency_ms = (time.monotonic() - start) * 1000
            return response
        except Exception as e:
            raise

    async def health(self, provider_name: Optional[str] = None) -> Dict[str, ProviderHealth]:
        all_providers = provider_registry.get_all()
        results: Dict[str, ProviderHealth] = {}
        to_check = [provider_name] if provider_name else list(all_providers.keys())
        for name in to_check:
            provider = all_providers.get(name)
            if not provider:
                results[name] = ProviderHealth(available=False, provider=name, error="Not registered")
                continue
            cached = await health_cache.get(name)
            if cached:
                results[name] = cached
                continue
            try:
                health = await provider.health()
                await health_cache.set(name, health)
                results[name] = health
            except Exception as e:
                results[name] = ProviderHealth(available=False, provider=name, error=str(e))
        return results

    async def list_models(self, provider_name: Optional[str] = None) -> Dict[str, List[ModelInfo]]:
        all_providers = provider_registry.get_all()
        results: Dict[str, List[ModelInfo]] = {}
        to_check = [provider_name] if provider_name else list(all_providers.keys())
        for name in to_check:
            provider = all_providers.get(name)
            if not provider:
                continue
            cached = await model_cache.get(name)
            if cached:
                results[name] = cached
                continue
            try:
                models = await provider.list_models()
                await model_cache.set(name, models)
                results[name] = models
            except Exception as e:
                logger.warning(f"Failed to list models for '{name}': {e}")
                results[name] = []
        return results

    def get_metrics(self, provider_name: Optional[str] = None) -> Dict[str, ProviderMetrics]:
        if provider_name:
            return {provider_name: self._metrics.get(provider_name, ProviderMetrics(provider=provider_name, model=""))}
        return dict(self._metrics)

    def _record_metrics(
        self, provider: str, model: str,
        tokens_in: int, tokens_out: int,
        latency_ms: float, cost: float,
        error: bool = False,
    ) -> None:
        key = f"{provider}:{model}"
        if key not in self._metrics:
            self._metrics[key] = ProviderMetrics(provider=provider, model=model)
        m = self._metrics[key]
        m.total_requests += 1
        if error:
            m.total_errors += 1
        m.total_tokens_input += tokens_in
        m.total_tokens_output += tokens_out
        m.total_latency_ms += latency_ms
        m.total_cost += cost
        m.last_request_at = __import__("datetime").datetime.utcnow().isoformat()


provider_manager = ProviderManager()
