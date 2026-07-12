"""Shared fixtures for the cross-service integration test suite (Issue #16).

Two layers of tests share this conftest:

1. In-process cross-service tests (always run): the real FastAPI apps for all
   five services are exercised over httpx ``ASGITransport`` so the gateway ->
   feed-assembly -> ranking path has genuine, runnable coverage without any
   external infrastructure.

2. Container-backed tests (``@pytest.mark.integration``): verify the isolated
   PostgreSQL/Redis/Kafka stack from ``docker-compose.test.yml``, pre-seeded
   with deterministic data. They skip automatically when the stack is down.
"""

import socket
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from services.feed_service.src.models.post import CandidatePost

# ---------------------------------------------------------------------------
# Deterministic identities (mirror tests/integration/fixtures/seed_test_data.sql)
# ---------------------------------------------------------------------------

VIEWER_ID = UUID("00000000-0000-0000-0000-000000000001")
AUTHOR_ALPHA = UUID("00000000-0000-0000-0000-000000000002")
AUTHOR_BETA = UUID("00000000-0000-0000-0000-000000000003")
AUTHOR_GAMMA = UUID("00000000-0000-0000-0000-000000000004")

POST_ALPHA_FRESH = UUID("aaaaaaaa-0000-0000-0000-000000000001")
POST_ALPHA_SECOND = UUID("aaaaaaaa-0000-0000-0000-000000000002")
POST_BETA_VIDEO = UUID("bbbbbbbb-0000-0000-0000-000000000001")
POST_BETA_OLD = UUID("bbbbbbbb-0000-0000-0000-000000000002")
POST_GAMMA_TRENDING = UUID("cccccccc-0000-0000-0000-000000000001")

SEEDED_USER_IDS = [VIEWER_ID, AUTHOR_ALPHA, AUTHOR_BETA, AUTHOR_GAMMA]
SEEDED_POST_IDS = [
    POST_ALPHA_FRESH,
    POST_ALPHA_SECOND,
    POST_BETA_VIDEO,
    POST_BETA_OLD,
    POST_GAMMA_TRENDING,
]

# Deterministic preferences for the viewer (matches user_preferences seed row).
VIEWER_PREFERENCES = {
    "author_affinities": {
        str(AUTHOR_ALPHA): 0.9,
        str(AUTHOR_BETA): 0.7,
    },
    "content_weights": {"text": 0.8, "image": 1.0, "video": 1.2, "link": 0.5},
}

# ---------------------------------------------------------------------------
# Isolated test infrastructure endpoints (docker-compose.test.yml)
# ---------------------------------------------------------------------------

TEST_POSTGRES_HOST = getenv("TEST_POSTGRES_HOST", "localhost")
TEST_POSTGRES_PORT = int(getenv("TEST_POSTGRES_PORT", "55432"))
TEST_POSTGRES_DSN = getenv(
    "TEST_POSTGRES_DSN",
    f"postgresql://test_user:test-password@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}"
    "/social_feed_test",
)
TEST_REDIS_HOST = getenv("TEST_REDIS_HOST", "localhost")
TEST_REDIS_PORT = int(getenv("TEST_REDIS_PORT", "56379"))
TEST_KAFKA_BOOTSTRAP = getenv("TEST_KAFKA_BOOTSTRAP", "localhost:19092")


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _require_stack_service(host: str, port: int, name: str) -> None:
    if not _port_open(host, port):
        pytest.skip(
            f"{name} test container not reachable at {host}:{port} "
            "(start it with: docker compose -f docker-compose.test.yml up -d --wait)"
        )


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    _require_stack_service(TEST_POSTGRES_HOST, TEST_POSTGRES_PORT, "PostgreSQL")
    pytest.importorskip("asyncpg", reason="asyncpg required for postgres integration tests")
    return TEST_POSTGRES_DSN


@pytest.fixture(scope="session")
def redis_endpoint() -> tuple[str, int]:
    _require_stack_service(TEST_REDIS_HOST, TEST_REDIS_PORT, "Redis")
    pytest.importorskip("redis", reason="redis-py required for redis integration tests")
    return TEST_REDIS_HOST, TEST_REDIS_PORT


@pytest.fixture(scope="session")
def kafka_bootstrap() -> str:
    host, _, port = TEST_KAFKA_BOOTSTRAP.partition(":")
    _require_stack_service(host, int(port or 9092), "Kafka")
    pytest.importorskip("aiokafka", reason="aiokafka required for kafka integration tests")
    return TEST_KAFKA_BOOTSTRAP


# ---------------------------------------------------------------------------
# In-process ASGI clients for every service
# ---------------------------------------------------------------------------


async def _asgi_client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def gateway_client(monkeypatch) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("ENVIRONMENT", "development")
    from services.api_gateway.src.main import app

    async for client in _asgi_client(app):
        yield client


@pytest.fixture
async def feed_client() -> AsyncIterator[AsyncClient]:
    from services.feed_service.src.main import app

    async for client in _asgi_client(app):
        yield client


@pytest.fixture
async def ranking_client() -> AsyncIterator[AsyncClient]:
    from services.ranking_engine.src.main import app

    async for client in _asgi_client(app):
        yield client


@pytest.fixture
async def profile_client() -> AsyncIterator[AsyncClient]:
    from services.user_profile.src.main import app

    async for client in _asgi_client(app):
        yield client


@pytest.fixture
async def ingestion_client() -> AsyncIterator[AsyncClient]:
    from services.content_ingestion.src.main import app

    async for client in _asgi_client(app):
        yield client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Real JWT for the seeded viewer, signed with the gateway's dev secret."""
    from services.api_gateway.src.auth.jwt_handler import create_access_token

    return {"Authorization": f"Bearer {create_access_token(VIEWER_ID)}"}


# ---------------------------------------------------------------------------
# Deterministic feed pipeline wiring
# ---------------------------------------------------------------------------


def build_seeded_candidates(
    now: datetime,
    extra_likes: dict[UUID, int] | None = None,
) -> tuple[list[CandidatePost], list[CandidatePost]]:
    """Build the deterministic candidate set mirroring seed_test_data.sql.

    ``created_at`` uses fixed offsets from ``now`` so recency-decay features are
    reproducible for ordering assertions on every run.

    Returns (following_candidates, trending_candidates).
    """
    extra = extra_likes or {}

    def likes(post_id: UUID, base: int) -> int:
        return base + extra.get(post_id, 0)

    following = [
        CandidatePost(
            post_id=POST_ALPHA_FRESH,
            author_id=AUTHOR_ALPHA,
            content_type="image",
            text_preview="Fresh high-engagement post from Alpha",
            media_url="https://cdn.test/alpha1.jpg",
            like_count=likes(POST_ALPHA_FRESH, 500),
            comment_count=100,
            share_count=50,
            has_media=True,
            text_length=88,
            hashtag_count=2,
            mutual_engagement_count=5,
            created_at=now - timedelta(hours=1),
        ),
        CandidatePost(
            post_id=POST_ALPHA_SECOND,
            author_id=AUTHOR_ALPHA,
            content_type="text",
            text_preview="Second post from Alpha.",
            like_count=likes(POST_ALPHA_SECOND, 40),
            comment_count=10,
            share_count=2,
            text_length=24,
            hashtag_count=1,
            mutual_engagement_count=2,
            created_at=now - timedelta(hours=3),
        ),
        CandidatePost(
            post_id=POST_BETA_VIDEO,
            author_id=AUTHOR_BETA,
            content_type="video",
            text_preview="Beta ships a video walkthrough of the ranking pipeline internals.",
            media_url="https://cdn.test/beta1.mp4",
            like_count=likes(POST_BETA_VIDEO, 120),
            comment_count=30,
            share_count=12,
            has_media=True,
            text_length=66,
            hashtag_count=1,
            mutual_engagement_count=3,
            created_at=now - timedelta(hours=6),
        ),
        CandidatePost(
            post_id=POST_BETA_OLD,
            author_id=AUTHOR_BETA,
            content_type="text",
            text_preview="Old low-engagement post from Beta.",
            like_count=likes(POST_BETA_OLD, 1),
            text_length=34,
            created_at=now - timedelta(hours=48),
        ),
    ]

    trending = [
        CandidatePost(
            post_id=POST_GAMMA_TRENDING,
            author_id=AUTHOR_GAMMA,
            content_type="image",
            text_preview="Trending post from Gamma sweeping the network right now.",
            media_url="https://cdn.test/gamma1.jpg",
            like_count=likes(POST_GAMMA_TRENDING, 3000),
            comment_count=800,
            share_count=400,
            has_media=True,
            text_length=57,
            hashtag_count=1,
            mutual_engagement_count=8,
            is_trending=True,
            created_at=now - timedelta(hours=2),
        ),
    ]
    return following, trending


class FeedPipelineHarness:
    """Wires deterministic candidate sources into the real feed-service app."""

    def __init__(self) -> None:
        self.extra_likes: dict[UUID, int] = {}
        self.following_calls = 0
        self.trending_calls = 0

    def invalidate_cache(self) -> None:
        from services.feed_service.src.api import feed_handler

        feed_handler.cache._store.clear()


@pytest.fixture
def feed_pipeline(monkeypatch) -> FeedPipelineHarness:
    """Deterministic feed pipeline: seeded candidates + isolated in-memory cache."""
    from services.feed_service.src.api import feed_handler

    harness = FeedPipelineHarness()
    harness.invalidate_cache()

    async def fake_following(user_id: UUID) -> list[CandidatePost]:
        harness.following_calls += 1
        following, trending = build_seeded_candidates(
            datetime.now(UTC), harness.extra_likes
        )
        # Include the trending post here too: the handler must deduplicate
        # overlapping candidates coming from both retrieval sources.
        return following + trending

    async def fake_trending() -> list[CandidatePost]:
        harness.trending_calls += 1
        _, trending = build_seeded_candidates(datetime.now(UTC), harness.extra_likes)
        return trending

    async def fake_preferences(user_id: UUID) -> dict:
        return VIEWER_PREFERENCES

    monkeypatch.setattr(feed_handler, "_get_following_candidates", fake_following)
    monkeypatch.setattr(feed_handler, "_get_trending_candidates", fake_trending)
    monkeypatch.setattr(feed_handler, "_get_user_preferences", fake_preferences)

    yield harness

    harness.invalidate_cache()
