"""Unit tests for the rate limiter (Redis fixed window + in-memory fallback)."""

import logging

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api_gateway.src.middleware.rate_limiter import (
    RateLimiterMiddleware,
    RedisFixedWindowLimiter,
    TokenBucket,
)


class TestTokenBucket:
    def test_initial_capacity(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_decrements(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.consume() is True
        assert bucket.tokens < 10.0

    def test_exhaustion_returns_false(self):
        bucket = TokenBucket(capacity=2.0, refill_rate=0.0)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False

    def test_refill_over_time(self):
        import time

        bucket = TokenBucket(capacity=5.0, refill_rate=1000.0)
        bucket.tokens = 0.0
        bucket.last_refill = time.monotonic() - 0.01
        assert bucket.consume() is True

    def test_capacity_cap(self):
        import time

        bucket = TokenBucket(capacity=5.0, refill_rate=1000.0)
        bucket.last_refill = time.monotonic() - 10
        bucket.consume()
        assert bucket.tokens <= 5.0


class TestRedisFixedWindowLimiter:
    async def test_consumption_decrements_remaining(self):
        limiter = RedisFixedWindowLimiter(fakeredis.aioredis.FakeRedis(), limit=5)

        allowed, remaining, _ = await limiter.check("user-a")
        assert allowed is True
        assert remaining == 4

        allowed, remaining, _ = await limiter.check("user-a")
        assert allowed is True
        assert remaining == 3

    async def test_keys_are_isolated(self):
        limiter = RedisFixedWindowLimiter(fakeredis.aioredis.FakeRedis(), limit=2)

        await limiter.check("user-a")
        await limiter.check("user-a")
        allowed_a, _, _ = await limiter.check("user-a")
        allowed_b, remaining_b, _ = await limiter.check("user-b")

        assert allowed_a is False
        assert allowed_b is True
        assert remaining_b == 1

    async def test_exhaustion_reports_retry_after(self):
        limiter = RedisFixedWindowLimiter(fakeredis.aioredis.FakeRedis(), limit=1)

        await limiter.check("user-a")
        allowed, remaining, retry_after = await limiter.check("user-a")

        assert allowed is False
        assert remaining == 0
        assert 0 < retry_after <= 60

    async def test_window_expiry_resets_count(self):
        client = fakeredis.aioredis.FakeRedis()
        limiter = RedisFixedWindowLimiter(client, limit=1)

        await limiter.check("user-a")
        allowed, _, _ = await limiter.check("user-a")
        assert allowed is False

        await client.delete("ratelimit:user-a")  # simulate window expiry
        allowed, _, _ = await limiter.check("user-a")
        assert allowed is True


def _build_app(**middleware_kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware, **middleware_kwargs)

    @app.get("/api/v1/thing")
    async def thing():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


class _BrokenRedis:
    """Stand-in client whose every pipeline blows up like a dead connection."""

    def pipeline(self, transaction: bool = True):
        raise ConnectionError("redis unreachable")


class TestMiddlewareRedisPath:
    def test_success_sets_remaining_header(self):
        app = _build_app(requests_per_minute=5, redis_client=fakeredis.aioredis.FakeRedis())
        with TestClient(app) as client:
            resp = client.get("/api/v1/thing", headers={"Authorization": "Bearer t1"})

        assert resp.status_code == 200
        assert resp.headers["X-RateLimit-Remaining"] == "4"

    def test_exhaustion_returns_429_with_retry_after(self):
        app = _build_app(requests_per_minute=2, redis_client=fakeredis.aioredis.FakeRedis())
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer t1"}
            assert client.get("/api/v1/thing", headers=headers).status_code == 200
            assert client.get("/api/v1/thing", headers=headers).status_code == 200

            resp = client.get("/api/v1/thing", headers=headers)

        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded. Try again shortly."
        assert int(resp.headers["Retry-After"]) >= 1

    def test_separate_auth_headers_get_separate_limits(self):
        app = _build_app(requests_per_minute=1, redis_client=fakeredis.aioredis.FakeRedis())
        with TestClient(app) as client:
            assert (
                client.get("/api/v1/thing", headers={"Authorization": "Bearer a"}).status_code
                == 200
            )
            assert (
                client.get("/api/v1/thing", headers={"Authorization": "Bearer a"}).status_code
                == 429
            )
            assert (
                client.get("/api/v1/thing", headers={"Authorization": "Bearer b"}).status_code
                == 200
            )

    def test_health_and_ready_exempt(self):
        app = _build_app(requests_per_minute=1, redis_client=fakeredis.aioredis.FakeRedis())
        with TestClient(app) as client:
            for _ in range(5):
                assert client.get("/health").status_code == 200


class TestMiddlewareFallback:
    def test_falls_back_to_in_memory_when_redis_unreachable(self, caplog: pytest.LogCaptureFixture):
        app = _build_app(requests_per_minute=2, redis_client=_BrokenRedis())
        with (
            caplog.at_level(logging.WARNING, logger="services.api_gateway.src.middleware"),
            TestClient(app) as client,
        ):
            headers = {"Authorization": "Bearer t1"}
            assert client.get("/api/v1/thing", headers=headers).status_code == 200
            assert client.get("/api/v1/thing", headers=headers).status_code == 200
            resp = client.get("/api/v1/thing", headers=headers)

        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "1"
        warnings = [r for r in caplog.records if "falling back" in r.getMessage()]
        assert len(warnings) == 1  # warned exactly once despite repeated failures

    def test_falls_back_when_redis_package_missing(self, monkeypatch: pytest.MonkeyPatch):
        from services.api_gateway.src.middleware import rate_limiter as rl

        monkeypatch.setattr(rl, "_REDIS_AVAILABLE", False)
        app = _build_app(requests_per_minute=3)
        with TestClient(app) as client:
            resp = client.get("/api/v1/thing", headers={"Authorization": "Bearer t1"})

        assert resp.status_code == 200
        assert "X-RateLimit-Remaining" in resp.headers

    def test_fallback_success_sets_remaining_header(self):
        app = _build_app(requests_per_minute=5, redis_client=_BrokenRedis())
        with TestClient(app) as client:
            resp = client.get("/api/v1/thing", headers={"Authorization": "Bearer t1"})

        assert resp.status_code == 200
        assert resp.headers["X-RateLimit-Remaining"] == "4"

    def test_rate_limit_env_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "7")
        middleware = RateLimiterMiddleware(FastAPI(), redis_client=fakeredis.aioredis.FakeRedis())
        assert middleware._limit == 7
