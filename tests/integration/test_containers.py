"""Container-backed integration tests against docker-compose.test.yml (Issue #16).

Verifies the isolated PostgreSQL/Redis/Kafka test stack: deterministic seed
data (fixed UUIDs, fixed timestamps), engagement aggregation, feed-cache
round-trips, and the Kafka engagement topic.

Start the stack first:
    docker compose -f docker-compose.test.yml up -d --wait

Every test here is marked ``integration`` and skips automatically when the
stack (or a client library) is unavailable, so CI without Docker stays green.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest

from tests.integration.conftest import (
    AUTHOR_ALPHA,
    POST_ALPHA_FRESH,
    POST_GAMMA_TRENDING,
    SEEDED_POST_IDS,
    SEEDED_USER_IDS,
    VIEWER_ID,
)

pytestmark = pytest.mark.integration

ENGAGEMENT_TOPIC = "engagement-events-test"


# ---------------------------------------------------------------------------
# PostgreSQL: deterministic seed data
# ---------------------------------------------------------------------------


class TestPostgresSeedData:
    async def test_seeded_users_have_fixed_uuids(self, postgres_dsn):
        import asyncpg

        conn = await asyncpg.connect(postgres_dsn)
        try:
            rows = await conn.fetch("SELECT id, username FROM users ORDER BY username")
            user_ids = {row["id"] for row in rows}
            assert set(SEEDED_USER_IDS) <= user_ids
            usernames = {row["username"] for row in rows}
            assert {"test_viewer", "author_alpha", "author_beta", "author_gamma"} <= usernames
        finally:
            await conn.close()

    async def test_seeded_posts_are_deterministic(self, postgres_dsn):
        import asyncpg

        conn = await asyncpg.connect(postgres_dsn)
        try:
            rows = await conn.fetch(
                "SELECT id, author_id, like_count, is_trending, created_at FROM posts"
            )
            by_id = {row["id"]: row for row in rows}
            assert set(SEEDED_POST_IDS) <= set(by_id)

            alpha_fresh = by_id[POST_ALPHA_FRESH]
            assert alpha_fresh["author_id"] == AUTHOR_ALPHA
            assert alpha_fresh["like_count"] == 500
            # Fixed timestamp from the seed file, not NOW().
            assert alpha_fresh["created_at"] == datetime(2026, 1, 10, 11, 0, tzinfo=UTC)

            assert by_id[POST_GAMMA_TRENDING]["is_trending"] is True
        finally:
            await conn.close()

    async def test_social_graph_seeded(self, postgres_dsn):
        import asyncpg

        conn = await asyncpg.connect(postgres_dsn)
        try:
            following = await conn.fetch(
                "SELECT followee_id FROM follows WHERE follower_id = $1", VIEWER_ID
            )
            assert len(following) == 2
        finally:
            await conn.close()

    async def test_engagement_aggregation_view(self, postgres_dsn):
        """New engagement events show up in the materialized aggregate."""
        import asyncpg

        conn = await asyncpg.connect(postgres_dsn)
        try:
            before = await conn.fetchrow(
                "SELECT like_count_total FROM post_engagement_agg WHERE post_id = $1",
                POST_ALPHA_FRESH,
            )
            baseline = before["like_count_total"] if before else 0

            await conn.execute(
                """
                INSERT INTO engagement_events (id, user_id, post_id, engagement_type, value)
                VALUES ($1, $2, $3, 'like', 1.0)
                """,
                uuid.uuid4(),
                VIEWER_ID,
                POST_ALPHA_FRESH,
            )
            await conn.execute("REFRESH MATERIALIZED VIEW post_engagement_agg")

            after = await conn.fetchrow(
                "SELECT like_count_total FROM post_engagement_agg WHERE post_id = $1",
                POST_ALPHA_FRESH,
            )
            assert after["like_count_total"] == baseline + 1
        finally:
            await conn.close()


# ---------------------------------------------------------------------------
# Redis: feed cache round-trip
# ---------------------------------------------------------------------------


class TestRedisFeedCache:
    async def test_feed_cache_roundtrip_with_ttl(self, redis_endpoint):
        import redis.asyncio as aioredis

        host, port = redis_endpoint
        client = aioredis.Redis(host=host, port=port, decode_responses=True)
        try:
            key = f"feed:test:{uuid.uuid4().hex[:8]}"
            payload = {
                "user_id": str(VIEWER_ID),
                "posts": [{"post_id": str(POST_ALPHA_FRESH), "position": 0}],
                "next_cursor": None,
            }
            await client.set(key, json.dumps(payload), ex=300)

            raw = await client.get(key)
            assert json.loads(raw) == payload

            ttl = await client.ttl(key)
            assert 0 < ttl <= 300

            await client.delete(key)
            assert await client.get(key) is None
        finally:
            await client.aclose()


# ---------------------------------------------------------------------------
# Kafka: engagement event round-trip
# ---------------------------------------------------------------------------


class TestKafkaEngagementPipeline:
    async def test_engagement_event_roundtrip(self, kafka_bootstrap):
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

        event = {
            "post_id": str(POST_ALPHA_FRESH),
            "user_id": str(VIEWER_ID),
            "engagement_type": "like",
            "value": 1,
            "nonce": uuid.uuid4().hex,
        }

        producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap)
        await producer.start()
        try:
            await producer.send_and_wait(
                ENGAGEMENT_TOPIC, json.dumps(event).encode()
            )
        finally:
            await producer.stop()

        consumer = AIOKafkaConsumer(
            ENGAGEMENT_TOPIC,
            bootstrap_servers=kafka_bootstrap,
            auto_offset_reset="earliest",
            group_id=f"it-{uuid.uuid4().hex[:8]}",
            consumer_timeout_ms=10_000,
        )
        await consumer.start()
        try:
            received = None
            async for message in consumer:
                candidate = json.loads(message.value)
                if candidate.get("nonce") == event["nonce"]:
                    received = candidate
                    break
            assert received == event
        finally:
            await consumer.stop()


# ---------------------------------------------------------------------------
# Cross-infrastructure health verification
# ---------------------------------------------------------------------------


class TestInfrastructureHealth:
    async def test_all_test_containers_healthy(
        self, postgres_dsn, redis_endpoint, kafka_bootstrap
    ):
        """Postgres answers queries, Redis answers PING, Kafka serves metadata."""
        import asyncpg
        import redis.asyncio as aioredis
        from aiokafka import AIOKafkaProducer

        conn = await asyncpg.connect(postgres_dsn)
        try:
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.close()

        host, port = redis_endpoint
        client = aioredis.Redis(host=host, port=port)
        try:
            assert await client.ping() is True
        finally:
            await client.aclose()

        producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap)
        await producer.start()
        try:
            partitions = await producer.partitions_for(ENGAGEMENT_TOPIC)
            assert partitions is not None
        finally:
            await producer.stop()
