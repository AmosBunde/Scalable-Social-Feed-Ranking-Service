"""Rate limiter middleware.

Primary path: a Redis-backed fixed-window counter (atomic INCR + EXPIRE NX
inside a MULTI/EXEC pipeline) so the limit is global across gateway replicas.

Fallback path: the original in-memory per-process token bucket, used when the
redis package is not installed or Redis is unreachable. Degradation is logged
as a warning once, and Redis is re-tried periodically.
"""

import logging
import os
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

try:  # pragma: no cover - exercised indirectly via _REDIS_AVAILABLE tests
    import redis.asyncio as aioredis

    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - gateway image may not ship redis yet
    aioredis = None  # type: ignore[assignment]
    _REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW_SECONDS = 60
_REDIS_RETRY_SECONDS = 30.0


@dataclass
class TokenBucket:
    capacity: float = 60.0
    refill_rate: float = 1.0  # tokens per second
    tokens: float = field(default=-1.0)
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        if self.tokens < 0:
            self.tokens = self.capacity

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RedisFixedWindowLimiter:
    """Fixed-window counter backed by Redis.

    Each check runs INCR + EXPIRE(NX) + TTL in a single MULTI/EXEC
    transaction, so counting is atomic per request and the window expiry is
    set exactly once per window regardless of replica interleaving.
    """

    def __init__(self, client: Any, limit: int, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self._client = client
        self._limit = limit
        self._window = window_seconds

    async def check(self, key: str) -> tuple[bool, int, int]:
        """Consume one request for ``key``.

        Returns (allowed, remaining, retry_after_seconds). Raises on any
        Redis error; callers are expected to fall back.
        """
        redis_key = f"ratelimit:{key}"
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, self._window, nx=True)
            pipe.ttl(redis_key)
            count, _, ttl = await pipe.execute()

        if ttl is None or ttl < 0:
            ttl = self._window
        allowed = count <= self._limit
        remaining = max(0, self._limit - count)
        return allowed, remaining, int(ttl)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int | None = None,
        redis_client: Any = None,
    ):
        super().__init__(app)
        if requests_per_minute is None:
            requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self._limit = requests_per_minute
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=float(requests_per_minute),
                refill_rate=requests_per_minute / 60.0,
            )
        )
        self._warned = False
        self._redis_down_until = 0.0
        self._redis_limiter: RedisFixedWindowLimiter | None = None

        client = redis_client if redis_client is not None else self._build_redis_client()
        if client is not None:
            self._redis_limiter = RedisFixedWindowLimiter(client, requests_per_minute)
        else:
            self._warn_once("redis package not installed")

    def _build_redis_client(self) -> Any:
        if not _REDIS_AVAILABLE:
            return None
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        return aioredis.Redis(
            host=host,
            port=port,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )

    def _warn_once(self, reason: str) -> None:
        if not self._warned:
            logger.warning(
                "Redis rate limiter unavailable (%s); falling back to "
                "per-replica in-memory token bucket",
                reason,
            )
            self._warned = True

    async def _check_redis(self, key: str) -> tuple[bool, int, int] | None:
        """Try the Redis limiter; return None when it should not be used."""
        if self._redis_limiter is None or time.monotonic() < self._redis_down_until:
            return None
        try:
            return await self._redis_limiter.check(key)
        except Exception as exc:
            self._warn_once(str(exc) or type(exc).__name__)
            self._redis_down_until = time.monotonic() + _REDIS_RETRY_SECONDS
            return None

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization", "")
        key = auth if auth else client_ip

        result = await self._check_redis(key)
        if result is not None:
            allowed, remaining, retry_after = result
            if not allowed:
                return self._rate_limited(max(1, retry_after))
        else:
            bucket = self._buckets[key]
            if not bucket.consume():
                return self._rate_limited(1)
            remaining = int(bucket.tokens)

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _rate_limited(retry_after: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again shortly."},
            headers={"Retry-After": str(retry_after)},
        )
