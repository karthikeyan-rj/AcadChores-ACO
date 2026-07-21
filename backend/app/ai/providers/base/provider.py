from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any

from app.ai.providers.base.types import (
    ProviderCapabilities,
    ProviderHealth,
    ModelInfo,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)


class ProviderConfig(ABC):
    name: str
    priority: int = 0
    enabled: bool = True


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier: 'ollama', 'openai', 'claude', etc."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Capabilities this provider supports."""

    @property
    @abstractmethod
    def config(self) -> ProviderConfig:
        """Provider-specific configuration."""

    @abstractmethod
    async def initialize(self) -> None:
        """Perform one-time startup initialization."""

    @abstractmethod
    async def generate(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request and return the full response.

        The request may carry api_key and base_url injected by the credential
        service. Providers must NOT access the database directly.
        """

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream a completion response token by token."""
        from app.ai.providers.base.exceptions import StreamingNotSupported
        raise StreamingNotSupported(self.name)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for input text. Only if supports_embeddings=True."""
        from app.ai.providers.base.exceptions import ProviderError
        raise ProviderError(f"Embeddings not supported by '{self.name}'", provider=self.name, recoverable=False)

    async def list_models(self) -> List[ModelInfo]:
        """List available models from this provider. Only if supports_model_discovery=True."""
        return []

    async def health(self) -> ProviderHealth:
        """Check provider availability and return health status."""
        return ProviderHealth(available=False, provider=self.name, error="Not implemented")

    async def shutdown(self) -> None:
        """Perform cleanup on shutdown."""
