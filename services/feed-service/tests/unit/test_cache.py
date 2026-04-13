"""Unit tests for feed cache."""
import pytest
from services.feed_service.src.cache.feed_cache import FeedCache


@pytest.fixture
def cache():
    return FeedCache()


class TestFeedCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set("key1", {"data": "value"})
        result = await cache.get("key1")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache):
        await cache.set("key1", {"data": "value"})
        await cache.invalidate("key1")
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_overwrite(self, cache):
        await cache.set("key1", {"v": 1})
        await cache.set("key1", {"v": 2})
        result = await cache.get("key1")
        assert result == {"v": 2}
