# ADR 004: PostgreSQL for Persistent Storage

## Status
Accepted

## Context
The system needs a relational database for users, posts, social graph (follows), engagement event history, and user preferences. Requirements include ACID transactions, complex joins for social graph queries, and materialized views for aggregation.

## Decision
Use PostgreSQL 16 with uuid-ossp for primary keys, JSONB for user preferences, array types for muted authors and hashtags, and a materialized view (post_engagement_agg) for windowed engagement counters.

## Consequences
- **Positive**: Mature, well-indexed relational model. Materialized views reduce real-time aggregation load. JSONB allows flexible preference schemas.
- **Negative**: Materialized view refresh latency (seconds). Social graph queries can be expensive at scale.
- **Mitigated**: Engagement counters also cached in Redis feature store. Graph queries limited to first-degree connections with index support.
