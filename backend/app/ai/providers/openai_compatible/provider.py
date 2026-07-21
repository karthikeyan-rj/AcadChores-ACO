import json
import time
import logging
from abc import abstractmethod
from typing import List, Optional, AsyncIterator, Dict, Any

import httpx

from app.ai.providers.base.provider import LLMProvider, ProviderConfig
from app.ai.providers.base.types import (
    ProviderCapabilities,
    ProviderHealth,
    ModelInfo,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
    MessageRole,
)
from app.ai.providers.base.exceptions import (
    ProviderUnavailable,
    ModelNotFound,
    InvalidResponse,
    ContextTooLarge,
    AuthenticationFailed,
    RateLimitExceeded,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleConfig(ProviderConfig):
    def __init__(
        self,
        name: str,
        base_url: str,
        default_model: str = "",
        api_key_env: str = "",
        priority: int = 0,
        enabled: bool = True,
        timeout_seconds: int = 120,
        supports_embeddings: bool = False,
        supports_model_discovery: bool = True,
        supports_structured_output: bool = False,
        supports_reasoning: bool = False,
        supports_vision: bool = False,
        supports_tools: bool = True,
        extra_headers: Optional[Dict[str, str]] = None,
        model_list_path: str = "/v1/models",
        chat_path: str = "/v1/chat/completions",
        embeddings_path: str = "/v1/embeddings",
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.api_key_env = api_key_env
        self.priority = priority
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.supported_embeddings = supports_embeddings
        self.supported_model_discovery = supports_model_discovery
        self.supported_structured_output = supports_structured_output
        self.supported_reasoning = supports_reasoning
        self.supported_vision = supports_vision
        self.supported_tools = supports_tools
        self.extra_headers = extra_headers or {}
        self.model_list_path = model_list_path
        self.chat_path = chat_path
        self.embeddings_path = embeddings_path


class OpenAICompatibleProvider(LLMProvider):
    """Reusable base for any provider exposing OpenAI-compatible chat completions.

    Subclasses override `config` to provide provider-specific settings.
    Credentials (api_key, base_url) are injected via CompletionRequest —
    providers never access the database directly.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def provider_config(self) -> OpenAICompatibleConfig:
        """Return the provider-specific configuration."""

    @property
    def name(self) -> str:
        return self.provider_config.name

    @property
    def capabilities(self) -> ProviderCapabilities:
        cfg = self.provider_config
        return ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=cfg.supported_embeddings,
            supports_model_discovery=cfg.supported_model_discovery,
            supports_structured_output=cfg.supported_structured_output,
            supports_reasoning=cfg.supported_reasoning,
            supports_system_prompt=True,
            supports_tools=cfg.supported_tools,
            supports_vision=cfg.supported_vision,
        )

    @property
    def config(self) -> OpenAICompatibleConfig:
        return self.provider_config

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(timeout=float(self.provider_config.timeout_seconds))
        logger.info(f"OpenAI-compatible provider '{self.name}' initialized: {self.provider_config.base_url}")

    def _resolve_auth(self, request: CompletionRequest) -> tuple[str, str]:
        """Resolve base_url and api_key. Request-level > config-level."""
        base_url = request.base_url or self.provider_config.base_url
        api_key = request.api_key or ""
        return base_url, api_key

    def _build_headers(self, api_key: str) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers.update(self.provider_config.extra_headers)
        return headers

    def _build_payload(self, request: CompletionRequest) -> Dict[str, Any]:
        model = request.model or self.provider_config.default_model

        messages = []
        for msg in request.messages:
            m: Dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            messages.append(m)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": request.stream,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = request.tools
        if request.response_format:
            payload["response_format"] = request.response_format

        return payload

    async def generate(self, request: CompletionRequest) -> CompletionResponse:
        if not self._client:
            raise ProviderUnavailable(self.name, "Provider not initialized")

        base_url, api_key = self._resolve_auth(request)
        if not api_key:
            raise AuthenticationFailed(self.name)

        model = request.model or self.provider_config.default_model
        payload = self._build_payload(request)
        payload["stream"] = False

        start = time.monotonic()
        try:
            response = await self._client.post(
                f"{base_url}{self.provider_config.chat_path}",
                json=payload,
                headers=self._build_headers(api_key),
            )
            latency_ms = (time.monotonic() - start) * 1000

            if response.status_code == 401:
                raise AuthenticationFailed(self.name)
            if response.status_code == 429:
                retry_after = float(response.headers.get("retry-after", "0"))
                raise RateLimitExceeded(self.name, retry_after=retry_after)
            if response.status_code == 404:
                raise ModelNotFound(model, self.name)
            if response.status_code != 200:
                text = response.text[:300]
                if "context" in text.lower() or "token" in text.lower():
                    raise ContextTooLarge(self.name, model)
                raise InvalidResponse(self.name, f"HTTP {response.status_code}: {text}")

            data = response.json()
            return self._parse_response(data, model, latency_ms)

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise ProviderUnavailable(self.name, f"Connection failed: {e}")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        if not self._client:
            raise ProviderUnavailable(self.name, "Provider not initialized")

        base_url, api_key = self._resolve_auth(request)
        if not api_key:
            raise AuthenticationFailed(self.name)

        payload = self._build_payload(request)
        payload["stream"] = True
        cancel_event = request.cancel_event

        try:
            async with self._client.stream(
                "POST",
                f"{base_url}{self.provider_config.chat_path}",
                json=payload,
                headers=self._build_headers(api_key),
            ) as response:
                if response.status_code == 401:
                    raise AuthenticationFailed(self.name)
                if response.status_code == 429:
                    raise RateLimitExceeded(self.name)
                if response.status_code != 200:
                    raise InvalidResponse(self.name, f"HTTP {response.status_code}")

                async for line in response.aiter_lines():
                    if cancel_event and hasattr(cancel_event, 'is_set') and cancel_event.is_set():
                        break
                    if not line.strip():
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.RequestError as e:
            raise ProviderUnavailable(self.name, f"Stream failed: {e}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self._client:
            raise ProviderUnavailable(self.name, "Provider not initialized")
        if not self.provider_config.supported_embeddings:
            raise ProviderUnavailable(self.name, "Embeddings not supported")

        api_key = request.api_key or ""
        if not api_key:
            raise AuthenticationFailed(self.name)

        base_url = request.base_url or self.provider_config.base_url
        model = request.model or self.provider_config.default_model

        payload = {"model": model, "input": request.input}
        start = time.monotonic()
        try:
            response = await self._client.post(
                f"{base_url}{self.provider_config.embeddings_path}",
                json=payload,
                headers=self._build_headers(api_key),
            )
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code == 401:
                raise AuthenticationFailed(self.name)
            if response.status_code != 200:
                raise InvalidResponse(self.name, f"HTTP {response.status_code}")

            data = response.json()
            embeddings = data.get("data", [{}])
            embedding = embeddings[0].get("embedding", []) if embeddings else []
            return EmbeddingResponse(
                embedding=embedding,
                model=data.get("model", model),
                provider=self.name,
                tokens_input=data.get("usage", {}).get("prompt_tokens", 0),
                latency_ms=latency_ms,
            )
        except httpx.RequestError as e:
            raise ProviderUnavailable(self.name, f"Embedding failed: {e}")

    async def list_models(self) -> List[ModelInfo]:
        if not self._client:
            return []
        if not self.provider_config.supported_model_discovery:
            return []

        try:
            response = await self._client.get(
                f"{self.provider_config.base_url}{self.provider_config.model_list_path}",
                headers=self._build_headers("dummy"),
                timeout=10.0,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                models.append(ModelInfo(
                    id=model_id,
                    provider=self.name,
                    name=model_id,
                    context_length=m.get("context_length"),
                    supports_structured_output=self.provider_config.supported_structured_output,
                    supports_reasoning=self.provider_config.supported_reasoning,
                    supports_vision=self.provider_config.supported_vision,
                    supports_tools=self.provider_config.supported_tools,
                    supports_embeddings=self.provider_config.supported_embeddings,
                    capabilities=self.capabilities,
                ))
            return models
        except Exception as e:
            logger.warning(f"Failed to list models for '{self.name}': {e}")
            return []

    async def health(self) -> ProviderHealth:
        start = time.monotonic()
        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=5.0)

            models = await self.list_models()
            latency_ms = (time.monotonic() - start) * 1000
            model_count = len(models)

            if model_count > 0 or self.provider_config.default_model:
                return ProviderHealth(
                    available=True,
                    provider=self.name,
                    model=self.provider_config.default_model,
                    latency_ms=latency_ms,
                )
            return ProviderHealth(
                available=False,
                provider=self.name,
                error="No models available",
                latency_ms=latency_ms,
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                provider=self.name,
                error=f"Health check failed: {e}",
            )

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _parse_response(self, data: Dict[str, Any], model: str, latency_ms: float) -> CompletionResponse:
        choices = data.get("choices", [])
        if not choices:
            raise InvalidResponse(self.name, "No choices in response")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "") or ""
        finish_reason = choice.get("finish_reason", "stop")
        tool_calls = message.get("tool_calls")

        usage = data.get("usage", {})
        return CompletionResponse(
            content=content,
            model=data.get("model", model),
            provider=self.name,
            finish_reason=finish_reason,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            tool_calls=tool_calls,
        )
