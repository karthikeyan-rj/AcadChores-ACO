from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional, Any

from app.ai.providers.base.types import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderMetrics,
    ModelInfo,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.ai.providers.base.exceptions import (
    ProviderUnavailable,
    ModelNotFound,
    StreamingNotSupported,
    ToolCallNotSupported,
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
        """Send a completion request and return the full response."""

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream a completion response token by token."""
        raise StreamingNotSupported(self.name)

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for input text."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Check provider availability and return health status."""

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models from this provider."""

    async def tool_call(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a tool/function call. Only valid when supports_tools=True."""
        raise ToolCallNotSupported(self.name)

    async def download_model(self, model_id: str) -> bool:
        """Download a model (Ollama-specific)."""
        raise ModelNotFound(model_id, self.name)

    async def delete_model(self, model_id: str) -> bool:
        """Delete a model (Ollama-specific)."""
        raise ModelNotFound(model_id, self.name)

    async def shutdown(self) -> None:
        """Perform cleanup on shutdown."""
