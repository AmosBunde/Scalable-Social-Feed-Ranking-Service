# ADR 001: Apache Kafka for Event Streaming

## Status
Accepted

## Context
The system needs an event streaming platform for: engagement events (likes, comments, shares), feed-served analytics events, feed invalidation signals, and model retraining data pipelines. Requirements include high throughput (100K+ events/sec), ordered delivery per partition, replay capability, and consumer group management.

## Decision
Use Apache Kafka 3.7 in KRaft mode (no ZooKeeper) with topic partitioning by user_id for engagement events and post_id for content events.

## Consequences
- **Positive**: Proven at LinkedIn-scale, exactly-once semantics with idempotent producers, consumer group rebalancing, infinite retention with tiered storage.
- **Negative**: Operational complexity, requires monitoring of consumer lag, partition rebalancing can cause temporary latency spikes.
- **Mitigated**: KRaft mode eliminates ZooKeeper dependency. Bitnami Kafka Docker image simplifies local dev.
