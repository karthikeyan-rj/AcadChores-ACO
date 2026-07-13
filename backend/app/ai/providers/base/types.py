from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncIterator


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ProviderCapabilities:
    supports_streaming: bool = False
    supports_json: bool = False
    supports_vision: bool = False
    supports_embeddings: bool = False
    supports_function_calling: bool = False
    supports_images: bool = False
    supports_system_prompt: bool = False
    supports_tools: bool = False


@dataclass
class ProviderHealth:
    available: bool
    provider: str
    model: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None
    gpu_available: bool = False
    gpu_count: int = 0
    memory_free: Optional[int] = None
    memory_total: Optional[int] = None


@dataclass
class ModelInfo:
    id: str
    provider: str
    name: str
    size_bytes: Optional[int] = None
    quantization: Optional[str] = None
    modified_at: Optional[str] = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)


@dataclass
class CompletionRequest:
    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None


@dataclass
class CompletionResponse:
    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class EmbeddingRequest:
    input: str
    model: Optional[str] = None


@dataclass
class EmbeddingResponse:
    embedding: List[float]
    model: str
    provider: str
    tokens_input: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0


@dataclass
class ProviderMetrics:
    provider: str
    model: str
    total_requests: int = 0
    total_errors: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    last_request_at: Optional[str] = None

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.total_errors) / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
