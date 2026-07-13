import asyncio
import time
import logging
from typing import Dict, Optional

from app.ai.providers.base.types import ProviderHealth

logger = logging.getLogger(__name__)


class HealthCache:
    def __init__(self, ttl_seconds: float = 30.0):
        self._ttl = ttl_seconds
        self._cache: Dict[str, ProviderHealth] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, provider_name: str) -> Optional[ProviderHealth]:
        async with self._lock:
            if provider_name in self._cache:
                age = time.monotonic() - self._timestamps[provider_name]
                if age < self._ttl:
                    return self._cache[provider_name]
        return None

    async def set(self, provider_name: str, health: ProviderHealth) -> None:
        async with self._lock:
            self._cache[provider_name] = health
            self._timestamps[provider_name] = time.monotonic()

    async def invalidate(self, provider_name: str) -> None:
        async with self._lock:
            self._cache.pop(provider_name, None)
            self._timestamps.pop(provider_name, None)

    async def invalidate_all(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._timestamps.clear()


health_cache = HealthCache()
