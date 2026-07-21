"""Centralized AI request router.

Single entry point for all AI completions. Handles:
- Local-only enforcement (cloud blocked when ai_local_only=True)
- Credential loading and injection into requests
- Cloud-to-local fallback with user notification
- Cancellation propagation via cancel_event
- Error classification for fallback decisions

Providers NEVER access the database. This router loads credentials,
decrypts them, and injects api_key/base_url into CompletionRequest.
"""
import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.ai.providers.base.types import (
    CompletionRequest,
    CompletionResponse,
    Message,
    ProviderHealth,
    ProviderMetrics,
)
from app.ai.providers.base.exceptions import (
    ProviderError,
    ProviderUnavailable,
    AuthenticationFailed,
    RateLimitExceeded,
    ContextTooLarge,
    InvalidResponse,
    ModelNotFound,
)
from app.ai.providers.base.health import health_cache
from app.ai.providers.base.cache import model_cache
from app.ai.registry import provider_registry
from app.services.credential_service import credential_service, CredentialError
from app.infrastructure.db.models import UserSettings

logger = logging.getLogger(__name__)

# Errors that should NOT be retried with fallback
NON_RETRYABLE_ERRORS = (AuthenticationFailed, ContextTooLarge)


class AIRouter:
    """Routes AI requests through local or cloud providers with fallback support."""

    def __init__(self):
        self._metrics: Dict[str, ProviderMetrics] = {}

    async def route_request(
        self,
        user_id: str,
        messages: List[Message],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        credential_id: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        reasoning_level: Optional[str] = None,
        cancel_event: Optional[Any] = None,
        fallback_to_local: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> CompletionResponse:
        """Route a completion request through the appropriate provider.

        Args:
            user_id: The user making the request (for credential loading).
            messages: Chat messages.
            provider: Preferred provider name (e.g. 'ollama', 'openai').
            model: Preferred model name.
            credential_id: Specific credential ID to use.
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
            response_format: JSON response format hint.
            reasoning_level: fast/balanced/deep — mapped to temperature/max_tokens.
            cancel_event: Threading event for cancellation.
            fallback_to_local: Whether to fall back to Ollama on cloud failure.
            system: System prompt to prepend.

        Returns:
            CompletionResponse from the selected provider.

        Raises:
            ProviderError: On unrecoverable provider failures.
        """
        from app.ai.providers.base.types import MessageRole

        settings_obj = await UserSettings.find_one(UserSettings.user_id == user_id)
        ai_local_only = getattr(settings_obj, 'ai_local_only', True) if settings_obj else True
        should_fallback = fallback_to_local if fallback_to_local is not None else (
            getattr(settings_obj, 'fallback_to_local', True) if settings_obj else True
        )

        effective_provider = provider or "ollama"
        effective_model = model

        if ai_local_only and effective_provider != "ollama":
            logger.info(f"Local-only mode: redirecting from '{effective_provider}' to 'ollama'")
            effective_provider = "ollama"

        temperature, max_tokens = self._apply_reasoning_level(reasoning_level, temperature, max_tokens)

        if system and not any(m.role == MessageRole.SYSTEM for m in messages):
            messages = [Message(role=MessageRole.SYSTEM, content=system)] + list(messages)

        if effective_provider == "ollama":
            return await self._route_ollama(
                messages=messages,
                model=effective_model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                cancel_event=cancel_event,
            )

        try:
            return await self._route_cloud(
                user_id=user_id,
                provider=effective_provider,
                model=effective_model,
                credential_id=credential_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                cancel_event=cancel_event,
            )
        except Exception as e:
            if not should_fallback:
                raise

            if self._is_non_retryable(e):
                raise

            logger.warning(
                f"Cloud provider '{effective_provider}' failed ({type(e).__name__}: {e}), "
                f"falling back to Ollama"
            )
            return await self._route_ollama(
                messages=messages,
                model=None,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                cancel_event=cancel_event,
                fallback_notice=f"Cloud provider '{effective_provider}' unavailable, using local Ollama",
            )

    async def _route_ollama(
        self,
        messages: List[Message],
        model: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict],
        cancel_event: Optional[Any],
        fallback_notice: Optional[str] = None,
    ) -> CompletionResponse:
        provider = provider_registry.get("ollama")
        if not provider:
            raise ProviderUnavailable("ollama", "Ollama provider not registered")

        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            cancel_event=cancel_event,
        )

        start = time.monotonic()
        try:
            response = await provider.generate(request)
            latency = (time.monotonic() - start) * 1000
            response.latency_ms = latency
            if fallback_notice:
                response.content = f"[{fallback_notice}]\n\n{response.content}"
            self._record_metrics("ollama", response.model or model or "",
                                 response.tokens_input, response.tokens_output,
                                 latency, 0.0, error=False)
            return response
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self._record_metrics("ollama", model or "", 0, 0, latency, 0.0, error=True)
            raise

    async def _route_cloud(
        self,
        user_id: str,
        provider: str,
        model: Optional[str],
        credential_id: Optional[str],
        messages: List[Message],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict],
        cancel_event: Optional[Any],
    ) -> CompletionResponse:
        decrypted_key, cred_doc = await credential_service.get_key_for_provider(
            user_id, provider, credential_id
        )

        llm_provider = provider_registry.get(provider)
        if not llm_provider:
            raise ProviderUnavailable(provider, f"Provider '{provider}' not registered")

        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            api_key=decrypted_key,
            cancel_event=cancel_event,
        )

        start = time.monotonic()
        try:
            response = await llm_provider.generate(request)
            latency = (time.monotonic() - start) * 1000
            response.latency_ms = latency
            self._record_metrics(provider, response.model or model or "",
                                 response.tokens_input, response.tokens_output,
                                 latency, 0.0, error=False)
            return response
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self._record_metrics(provider, model or "", 0, 0, latency, 0.0, error=True)
            raise

    def _apply_reasoning_level(
        self,
        reasoning_level: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> tuple:
        if not reasoning_level:
            return temperature, max_tokens

        level_map = {
            "fast": {"temperature": 0.0, "max_tokens": 1024},
            "balanced": {"temperature": 0.0, "max_tokens": 4096},
            "deep": {"temperature": 0.3, "max_tokens": 8192},
        }
        level = level_map.get(reasoning_level)
        if level:
            return level["temperature"], level["max_tokens"]
        return temperature, max_tokens

    def _is_non_retryable(self, error: Exception) -> bool:
        for exc_type in NON_RETRYABLE_ERRORS:
            if isinstance(error, exc_type):
                return True
        if isinstance(error, ProviderError) and not error.recoverable:
            return True
        return False

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
        m.last_request_at = datetime.now(timezone.utc).isoformat()

    def get_metrics(self, provider_name: Optional[str] = None) -> Dict[str, ProviderMetrics]:
        if provider_name:
            return {k: v for k, v in self._metrics.items() if k.startswith(f"{provider_name}:")}
        return dict(self._metrics)

    async def health_check(self, provider_name: Optional[str] = None) -> Dict[str, ProviderHealth]:
        """Check health of one or all providers."""
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


ai_router = AIRouter()
