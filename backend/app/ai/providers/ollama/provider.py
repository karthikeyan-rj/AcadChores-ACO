import json
import time
import logging
from typing import List, Optional, AsyncIterator, Dict, Any

import httpx

from app.ai.providers.base.provider import LLMProvider
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
)
from app.ai.providers.ollama.config import ollama_config, OllamaConfig
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._cfg = ollama_config

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_json=True,
            supports_vision=False,
            supports_embeddings=True,
            supports_function_calling=True,
            supports_images=False,
            supports_system_prompt=True,
            supports_tools=True,
        )

    @property
    def config(self) -> OllamaConfig:
        return self._cfg

    async def initialize(self) -> None:
        base_url = settings.OLLAMA_BASE_URL or self._cfg.base_url
        model = settings.OLLAMA_MODEL or self._cfg.model
        timeout_seconds = getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 180)
        self._cfg.base_url = base_url.rstrip("/")
        self._cfg.model = model
        self._client = httpx.AsyncClient(timeout=float(timeout_seconds))
        logger.info(f"Ollama provider initialized: {self._cfg.base_url}, model={self._cfg.model}, timeout={timeout_seconds}s")

    async def generate(self, request: CompletionRequest) -> CompletionResponse:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        model = request.model or self._cfg.model
        prompt, system, messages = self._build_ollama_prompt(request.messages)

        options: Dict[str, Any] = {"temperature": request.temperature}
        if request.max_tokens:
            options["num_predict"] = request.max_tokens

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
            "keep_alive": self._cfg.keep_alive,
        }
        if system:
            payload["system"] = system

        if request.response_format and request.response_format.get("type") == "json_object":
            payload["format"] = "json"

        start = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._cfg.base_url}/api/generate",
                json=payload,
            )
            latency_ms = (time.monotonic() - start) * 1000

            if response.status_code == 404:
                raise ModelNotFound(model, self.name)
            if response.status_code != 200:
                text = response.text[:200]
                if "token limit" in text.lower() or "context length" in text.lower():
                    raise ContextTooLarge(self.name, model, context_length=0)
                raise InvalidResponse(self.name, f"HTTP {response.status_code}: {text}")

            data = response.json()
            content = data.get("response", "")

            return CompletionResponse(
                content=content,
                model=data.get("model", model),
                provider=self.name,
                finish_reason="stop",
                tokens_input=data.get("prompt_eval_count", 0),
                tokens_output=data.get("eval_count", 0),
                latency_ms=latency_ms,
                cost=0.0,
            )
        except httpx.RequestError as e:
            raise ProviderUnavailable(self.name, f"Connection failed: {e}")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        model = request.model or self._cfg.model
        prompt, system, messages = self._build_ollama_prompt(request.messages)

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": request.temperature},
            "keep_alive": self._cfg.keep_alive,
        }
        if system:
            payload["system"] = system

        try:
            async with self._client.stream(
                "POST",
                f"{self._cfg.base_url}/api/generate",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    raise InvalidResponse(self.name, f"HTTP {response.status_code}")
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.RequestError as e:
            raise ProviderUnavailable(self.name, f"Stream connection failed: {e}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        model = request.model or self._cfg.model
        start = time.monotonic()
        try:
            response = await self._client.post(
                f"{self._cfg.base_url}/api/embeddings",
                json={"model": model, "prompt": request.input},
            )
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code != 200:
                raise InvalidResponse(self.name, f"HTTP {response.status_code}")
            data = response.json()
            return EmbeddingResponse(
                embedding=data.get("embedding", []),
                model=data.get("model", model),
                provider=self.name,
                latency_ms=latency_ms,
                cost=0.0,
            )
        except httpx.RequestError as e:
            raise ProviderUnavailable(self.name, f"Embedding failed: {e}")

    async def health(self) -> ProviderHealth:
        start = time.monotonic()
        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=5.0)
            response = await self._client.get(f"{self._cfg.base_url}/api/tags", timeout=5.0)
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                model_available = any(
                    m.get("name", "") == self._cfg.model
                    for m in models
                ) if models else False
                if not model_available and models:
                    # Also check partial match (without tag)
                    base_model = self._cfg.model.split(":")[0]
                    model_available = any(
                        m.get("name", "").startswith(base_model)
                        for m in models
                    )
                if not model_available and models:
                    logger.warning(
                        f"Required model '{self._cfg.model}' not found. "
                        f"Available models: {model_names}. "
                        f"Run: ollama pull {self._cfg.model}"
                    )
                return ProviderHealth(
                    available=True,
                    provider=self.name,
                    model=self._cfg.model,
                    latency_ms=latency_ms,
                    gpu_available=False,
                )
            return ProviderHealth(
                available=False,
                provider=self.name,
                error=f"HTTP {response.status_code}",
                latency_ms=latency_ms,
            )
        except Exception as e:
            return ProviderHealth(
                available=False,
                provider=self.name,
                error=f"Unable to connect to Ollama at {self._cfg.base_url}. "
                      f"Ensure Ollama is running and {self._cfg.model} is installed. "
                      f"Error: {e}",
            )

    async def list_models(self) -> List[ModelInfo]:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        try:
            response = await self._client.get(f"{self._cfg.base_url}/api/tags", timeout=10.0)
            if response.status_code != 200:
                return []
            data = response.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                models.append(ModelInfo(
                    id=name,
                    provider=self.name,
                    name=name,
                    size_bytes=m.get("size", 0),
                    quantization=m.get("details", {}).get("quantization", ""),
                    modified_at=m.get("modified_at", ""),
                    capabilities=self.capabilities,
                ))
            return models
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    async def download_model(self, model_id: str) -> bool:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        try:
            response = await self._client.post(
                f"{self._cfg.base_url}/api/pull",
                json={"name": model_id, "stream": False},
                timeout=600.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to download model {model_id}: {e}")
            return False

    async def delete_model(self, model_id: str) -> bool:
        if not self._client:
            raise ProviderUnavailable("Ollama client not initialized")
        try:
            response = await self._client.delete(
                f"{self._cfg.base_url}/api/delete",
                json={"name": model_id},
                timeout=30.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to delete model {model_id}: {e}")
            return False

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_ollama_prompt(self, messages: List[Message]):
        system = None
        parts = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system = msg.content
            elif msg.role == MessageRole.USER:
                parts.append(f"User: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                parts.append(f"Assistant: {msg.content}")
            else:
                parts.append(msg.content)
        prompt = "\n".join(parts)
        if not prompt.endswith("\nAssistant:"):
            prompt += "\nAssistant:"
        return prompt, system, messages
