"""Redis client wrapper with circuit breaker, serialization, and TTL management."""

import json
import logging
from collections.abc import Awaitable
from datetime import timedelta
from typing import Any, cast

from services.shared.src.events.kafka_client import CircuitBreaker

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis

    class RedisClient:
        """Async Redis client with circuit breaker and typed get/set."""

        def __init__(
            self,
            host: str = "localhost",
            port: int = 6379,
            password: str | None = None,
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
                # redis-py types ping() as Awaitable[bool] | bool; the async client awaits
                return await cast(Awaitable[bool], self._client.ping())
            except Exception:
                return False

        async def get(self, key: str) -> dict[str, Any] | None:
            if not self._circuit.is_callable:
                logger.warning("Redis circuit open, skipping get for %s", key)
                return None
            try:
                raw = await self._client.get(key)
                self._circuit.record_success()
                if raw is None:
                    return None
                data: dict[str, Any] = json.loads(raw)
                return data
            except Exception as exc:
                self._circuit.record_failure()
                logger.error("Redis get failed for %s: %s", key, exc)
                return None

        async def set(
            self,
            key: str,
            value: dict[str, Any],
            ttl: timedelta | None = None,
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

        async def increment(self, key: str, amount: int = 1) -> int | None:
            try:
                return int(await self._client.incrby(key, amount))
            except Exception as exc:
                logger.error("Redis increment failed for %s: %s", key, exc)
                return None

        async def close(self) -> None:
            await self._pool.disconnect()

except ImportError:
    logger.info("redis not installed; RedisClient unavailable")
