"""Unit tests for the engagement consumer."""

from uuid import uuid4

import pytest

from services.content_ingestion.src.consumers.engagement_consumer import EngagementConsumer


@pytest.fixture
def consumer():
    return EngagementConsumer()


class TestEngagementConsumer:
    @pytest.mark.asyncio
    async def test_handle_like_event(self, consumer):
        event = {"post_id": str(uuid4()), "engagement_type": "like", "value": 1}
        await consumer.handle_event(event)
        key = f"{event['post_id']}:like"
        assert consumer._counters[key]["total"] == 1

    @pytest.mark.asyncio
    async def test_accumulates_counts(self, consumer):
        post_id = str(uuid4())
        for _ in range(5):
            await consumer.handle_event({"post_id": post_id, "engagement_type": "like", "value": 1})
        assert consumer._counters[f"{post_id}:like"]["total"] == 5

    @pytest.mark.asyncio
    async def test_malformed_event_ignored(self, consumer):
        await consumer.handle_event({"bad": "data"})
        assert len(consumer._counters) == 0

    @pytest.mark.asyncio
    async def test_spike_detection(self, consumer):
        post_id = str(uuid4())
        for _ in range(50):
            await consumer.handle_event({"post_id": post_id, "engagement_type": "like", "value": 1})
        assert consumer._counters[f"{post_id}:like"]["window_1h"] >= 50
