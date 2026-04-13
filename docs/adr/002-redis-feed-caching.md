# ADR 002: Redis for Feed Caching

## Status
Accepted

## Context
The feed service needs a low-latency cache layer to avoid recomputing ranked feeds on every request. The cache must support: sub-millisecond reads, TTL-based expiration, key-value storage for JSON payloads, and graceful degradation when unavailable.

## Decision
Use Redis 7.x (cluster mode in production, standalone for dev) with a 300-second TTL for ranked feeds and 3600-second TTL for feature store data. Cache keys use SHA256 hashes of user_id and cursor to prevent key collision.

## Consequences
- **Positive**: p50 latency drops from ~35ms (cold) to ~3ms (cached). Reduces load on ranking engine and PostgreSQL by 80%+ for active users.
- **Negative**: Cache invalidation on engagement spikes requires coordination with content ingestion service. Stale feeds possible within TTL window.
- **Mitigated**: Circuit breaker in Redis client allows graceful fallback to cold feeds. LRU eviction policy with 256MB cap for local dev.
