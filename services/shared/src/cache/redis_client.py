"""Redis client wrapper with circuit breaker, serialization, and TTL management."""
import json
import logging
from datetime import timedelta
from typing import Any, Optional

import redis.asyncio as aioredis

from services.shared.src.events.kafka_client import CircuitBreaker

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client with circuit breaker and typed get/set."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        default_ttl: timedelta = timedelta(seconds=300),
    ) -> None:
        self.default_ttl = default_ttl
        self._circuit = CircuitBreaker(failure_threshold=3)
        self._pool = aioredis.ConnectionPool.from_url(
            f"redis://{host}:{port}/{db}",
            password=password,
            max_connections=50,
            decode_responses=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    async def ping(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self._circuit.is_callable:
            logger.warning("Redis circuit open, skipping get for %s", key)
            return None
        try:
            raw = await self._client.get(key)
            self._circuit.record_success()
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            self._circuit.record_failure()
            logger.error("Redis get failed for %s: %s", key, exc)
            return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> bool:
        if not self._circuit.is_callable:
            logger.warning("Redis circuit open, skipping set for %s", key)
            return False
        try:
            effective_ttl = ttl or self.default_ttl
            await self._client.setex(
                key,
                int(effective_ttl.total_seconds()),
                json.dumps(value, default=str),
            )
            self._circuit.record_success()
            return True
        except Exception as exc:
            self._circuit.record_failure()
            logger.error("Redis set failed for %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self._client.delete(key)
            return True
        except Exception as exc:
            logger.error("Redis delete failed for %s: %s", key, exc)
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        try:
            return await self._client.incrby(key, amount)
        except Exception as exc:
            logger.error("Redis increment failed for %s: %s", key, exc)
            return None

    async def close(self) -> None:
        await self._pool.disconnect()
