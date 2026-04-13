# Session Flow: Feed Request Lifecycle

## Overview

When a user opens the app, the feed request traverses 7 stages with a target latency of p50 < 30ms (cached) and p99 < 80ms (cold).

## Stages

### Stage 1: Authentication (Gateway, ~2ms)
The API gateway receives `GET /api/v1/feed?user_id=xxx&cursor=yyy` with a JWT bearer token. It validates the token signature and expiration, extracts the user_id from the payload, and checks the token bucket rate limiter. If the rate limit is exceeded, it returns 429 with a Retry-After header.

### Stage 2: Cache Check (Feed Service, ~1ms)
The feed service computes a cache key using `SHA256(user_id + cursor)` and checks Redis. On a cache hit, the pre-ranked feed is returned immediately, skipping stages 3 through 6. Cache TTL is 300 seconds.

### Stage 3: Parallel Fan-Out (~12ms)
Three concurrent requests are dispatched using `asyncio.gather`:
- **User Profile**: returns follow graph (~200 user IDs) and content preferences
- **Content Ingestion**: returns trending posts (~50) and algorithmic suggestions (~50)
- **Feature Store**: returns engagement features for candidate enrichment

### Stage 4: Candidate Retrieval and Deduplication
Following candidates (~200) are merged with trending (~50) and explore (~50) candidates. Posts are deduplicated by post_id, yielding ~300 unique candidates. Each candidate is enriched with engagement counters from the feature store.

### Stage 5: ML Scoring (~15ms)
The 300 enriched feature vectors are sent as a single batch to the ranking engine. XGBoost computes a relevance score per candidate based on 6 feature groups:
- Author affinity (0.25 weight)
- Engagement velocity (0.20)
- Recency decay with 6h half-life (0.20)
- Content type preference (0.15)
- Social proof (0.10)
- Post quality (0.10)

### Stage 6: Diversify + Assemble (~2ms)
The diversifier enforces business rules on the scored list:
- Max 2 posts per author in any sliding window of 10
- At least 1 image/video in every window of 5
- Trending posts interleaved at positions 3, 8, 15

The assembler constructs the paginated response with base64-encoded cursor for the next page. Default page size is 25 posts.

### Stage 7: Cache + Emit (~3ms)
The ranked feed is written to Redis with 300s TTL. A `feed-served` event is published to Kafka asynchronously, containing user_id, feed_size, model_version, latency_ms, cache_hit, and post_ids. This event feeds the analytics pipeline and model retraining loop.

## Latency Budget

| Stage | Target | Notes |
|-------|--------|-------|
| Auth | 2ms | JWT signature verification |
| Cache check | 1ms | Redis GET |
| Fan-out | 12ms | Parallel, dominated by slowest call |
| Scoring | 15ms | XGBoost batch inference |
| Diversify | 1ms | In-memory rule engine |
| Assemble | 1ms | Pagination + serialization |
| Cache + Emit | 3ms | Redis SET + async Kafka |
| **Total (cold)** | **~35ms** | **Target p50** |
| **Total (cached)** | **~3ms** | **Skip stages 3-6** |

## Error Handling

- **Redis down**: Circuit breaker opens, all feeds are cold (no caching). Degraded but functional.
- **Ranking engine down**: Feed service falls back to heuristic scorer (weighted sum). Quality degrades, service stays up.
- **Kafka down**: Feed-served events are dropped. Feed generation continues. Events are logged locally for replay.
- **User Profile down**: Feed uses default preferences and empty follow graph. Only trending/explore candidates shown.
