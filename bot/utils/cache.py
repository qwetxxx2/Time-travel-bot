import asyncio
from typing import Any, Awaitable, Callable

from cachetools import TTLCache


class SimpleTTLCache:
    """Кэш в памяти с TTL (потокобезопасный для asyncio)."""

    def __init__(self, maxsize: int = 128, ttl: int = 3600) -> None:
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = value

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        value = await self.get(key)
        if value is None:
            value = await factory()
            if value:  # пустые результаты не кэшируем
                await self.set(key, value)
        return value