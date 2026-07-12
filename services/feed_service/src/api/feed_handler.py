"""Feed handler: orchestrates candidate retrieval, scoring, diversification, and assembly."""

import asyncio
import hashlib
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Query

from services.feed_service.src.cache.feed_cache import FeedCache
from services.feed_service.src.models.feed import FeedResponse
from services.feed_service.src.models.post import CandidatePost
from services.feed_service.src.ranking.assembler import FeedAssembler
from services.feed_service.src.ranking.diversifier import FeedDiversifier
from services.feed_service.src.ranking.scorer import FeedScorer

logger = logging.getLogger(__name__)
router = APIRouter()

scorer = FeedScorer()
diversifier = FeedDiversifier()
assembler = FeedAssembler()
cache = FeedCache()


def _cache_key(user_id: UUID, cursor: str | None) -> str:
    raw = f"feed:{user_id}:{cursor or 'head'}"
    return f"feed:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    user_id: UUID,
    cursor: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
):
    start = time.monotonic()
    cache_key = _cache_key(user_id, cursor)

    # Step 1: Check cache
    cached = await cache.get(cache_key)
    if cached:
        latency_ms = (time.monotonic() - start) * 1000
        logger.info("Cache hit for user %s, latency=%.1fms", user_id, latency_ms)
        return FeedResponse(**cached)

    # Step 2: Fan-out candidate retrieval (parallel)
    following_task = asyncio.create_task(_get_following_candidates(user_id))
    trending_task = asyncio.create_task(_get_trending_candidates())
    preferences_task = asyncio.create_task(_get_user_preferences(user_id))

    following_candidates, trending_candidates, preferences = await asyncio.gather(
        following_task, trending_task, preferences_task
    )

    # Step 3: Deduplicate
    seen_ids: set[UUID] = set()
    candidates: list[CandidatePost] = []
    for post in following_candidates + trending_candidates:
        if post.post_id not in seen_ids:
            seen_ids.add(post.post_id)
            candidates.append(post)

    # Step 4: Score
    scored = await scorer.score_batch(candidates, preferences)

    # Step 5: Diversify
    diversified = diversifier.apply_rules(scored)

    # Step 6: Assemble with pagination
    feed_response = assembler.assemble(
        posts=diversified,
        user_id=user_id,
        limit=limit,
        cursor=cursor,
    )

    # Step 7: Cache
    await cache.set(cache_key, feed_response.model_dump(mode="json"))

    latency_ms = (time.monotonic() - start) * 1000
    logger.info(
        "Cold feed for user %s, %d posts, latency=%.1fms",
        user_id,
        len(feed_response.posts),
        latency_ms,
    )

    return feed_response


async def _get_following_candidates(user_id: UUID) -> list[CandidatePost]:
    """Retrieve posts from followed users. Placeholder for inter-service call."""
    return []


async def _get_trending_candidates() -> list[CandidatePost]:
    """Retrieve trending posts. Placeholder for inter-service call."""
    return []


async def _get_user_preferences(user_id: UUID) -> dict:
    """Fetch user preferences from user-profile service."""
    return {}
