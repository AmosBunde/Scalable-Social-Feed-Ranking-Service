"""Feed cache: Redis-backed cache for ranked feeds."""

import logging
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)


class FeedCache:
    """Feed caching layer. Uses RedisClient in production, in-memory dict for dev."""

    def __init__(self, ttl_seconds: int = 300):
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[str, dict[str, Any]] = {}
        self._redis = None

    async def get(self, key: str) -> dict[str, Any] | None:
        if self._redis:
            return await self._redis.get(key)
        return self._store.get(key)

    async def set(self, key: str, value: dict[str, Any]) -> bool:
        if self._redis:
            return await self._redis.set(key, value, ttl=self._ttl)
        self._store[key] = value
        return True

    async def invalidate(self, key: str) -> bool:
        if self._redis:
            return await self._redis.delete(key)
        self._store.pop(key, None)
        return True
