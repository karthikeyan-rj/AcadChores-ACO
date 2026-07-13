import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.ai.providers.base.types import (
    Message, MessageRole, CompletionResponse, ProviderHealth,
    ModelInfo, ProviderMetrics,
)
from app.ai.providers.base.exceptions import ProviderError
from app.ai.manager import provider_manager

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self._provider_manager = provider_manager

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[str] = None,
    ) -> str:
        messages = []
        if system:
            messages.append(Message(role=MessageRole.SYSTEM, content=system))
        messages.append(Message(role=MessageRole.USER, content=prompt))

        fmt = None
        if response_format == "json":
            fmt = {"type": "json_object"}

        response = await self._provider_manager.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=fmt,
            preferred_provider=preferred_provider,
        )
        return response.content

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        preferred_provider: Optional[str] = None,
    ) -> CompletionResponse:
        messages = []
        if system:
            messages.append(Message(role=MessageRole.SYSTEM, content=system))
        messages.append(Message(role=MessageRole.USER, content=prompt))

        return await self._provider_manager.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            preferred_provider=preferred_provider,
        )

    async def health(self, provider_name: Optional[str] = None) -> Dict[str, ProviderHealth]:
        return await self._provider_manager.health(provider_name)

    async def list_models(self, provider_name: Optional[str] = None) -> Dict[str, List[ModelInfo]]:
        return await self._provider_manager.list_models(provider_name)

    def get_metrics(self, provider_name: Optional[str] = None) -> Dict[str, ProviderMetrics]:
        return self._provider_manager.get_metrics(provider_name)


llm_service = LLMService()
