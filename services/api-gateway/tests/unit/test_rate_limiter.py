"""Unit tests for token bucket rate limiter."""
import pytest
from services.api_gateway.src.middleware.rate_limiter import TokenBucket


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
