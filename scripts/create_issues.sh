#!/usr/bin/env bash
# create_issues.sh — Creates all 20 GitHub issues for the Scalable Social Feed Ranking Service
# Usage: chmod +x create_issues.sh && ./create_issues.sh
# Requires: gh CLI authenticated (gh auth login)

set -euo pipefail

REPO="AmosBunde/Scalable-Social-Feed-Ranking-Service"

echo "Creating issues for $REPO..."
echo "============================================"

# ─── Milestone 1: Foundation ───

gh issue create --repo "$REPO" \
  --title "feat: Project scaffolding and shared libraries" \
  --label "feat,priority:critical,milestone:foundation" \
  --body '## Issue #1: Project scaffolding and shared libraries

### Description
Set up the monorepo structure with all service directories, shared libraries (Kafka client with circuit breaker, Redis client, structured logging, OpenTelemetry tracing), and Pydantic base models (PostEvent, EngagementEvent, FeedServedEvent, UserPreferences, PaginationCursor). Include pyproject.toml for each service.

### Files to create
```
services/shared/src/models/base.py          — Pydantic base models
services/shared/src/events/kafka_client.py  — Async Kafka producer/consumer + CircuitBreaker
services/shared/src/cache/redis_client.py   — Async Redis client + circuit breaker
services/shared/src/utils/logging.py        — Structured JSON logging + OTEL tracer factory
services/shared/tests/test_circuit_breaker.py
pyproject.toml                              — Root pytest/ruff/mypy config
requirements-dev.txt
.gitignore
All __init__.py files across service directories
```

### Acceptance Criteria
- [ ] All service directories created with `src/` and `tests/` structure
- [ ] Shared Kafka client with circuit breaker (CLOSED → OPEN → HALF_OPEN states)
- [ ] Shared Redis client with TTL management and circuit breaker
- [ ] Structured JSON logging with service name correlation
- [ ] OpenTelemetry tracer factory (no-op when unconfigured)
- [ ] Unit tests for circuit breaker (5 test cases minimum)
- [ ] All `__init__.py` files present for Python package resolution
- [ ] `pyproject.toml` configures pytest, ruff, mypy
- [ ] `requirements-dev.txt` pins all dependencies

### Implementation Command
```bash
claude -p "Read the skill at skill/SKILL.md. Implement Issue #1: Create all shared libraries (kafka_client.py with circuit breaker, redis_client.py, logging.py, base models). Include all unit tests. Follow the exact file paths in the skill."
git add -A && git commit -m "feat: project scaffolding and shared libraries (#1)"
```'

echo "✓ Issue #1 created"

gh issue create --repo "$REPO" \
  --title "feat: PostgreSQL schema and seed data" \
  --label "feat,priority:critical,milestone:foundation" \
  --body '## Issue #2: PostgreSQL schema and seed data

### Description
Create the database schema with tables for users, posts, follows (social graph), engagement_events (append-only), user_preferences, and a materialized view for post_engagement_agg with windowed counters (1h, 24h). Add seed script generating 50 users, 500 posts, random follow graph, and 2000 engagement events.

### Files to create
```
scripts/init-db.sql      — Full DDL with tables, indexes, materialized view
scripts/seed_data.py     — Python script generating sample data
```

### Schema Tables
- `users` — UUID PK, username, display_name, bio, follower/following counts, timestamps
- `posts` — UUID PK, author_id FK, content_type, text, media_url, hashtags[], engagement counts, is_trending
- `follows` — composite PK (follower_id, followee_id), timestamps
- `engagement_events` — append-only, user_id, post_id, engagement_type, value, dwell_time_ms
- `user_preferences` — JSONB content_weights, UUID[] muted_authors
- `post_engagement_agg` — materialized view with windowed counters

### Acceptance Criteria
- [ ] `init-db.sql` with all tables, indexes, and materialized view
- [ ] UUID primary keys with `uuid-ossp` extension
- [ ] Proper indexes on `posts(author_id)`, `posts(created_at DESC)`, `engagement_events(post_id)`
- [ ] `seed_data.py` generates 50 users, 500 posts, ~1000 follows, 2000 engagements
- [ ] Script outputs to `scripts/seed-data.json`

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #2: Create scripts/init-db.sql with full schema (users, posts, follows, engagement_events, materialized view, user_preferences) and scripts/seed_data.py."
git add -A && git commit -m "feat: postgresql schema and seed data (#2)"
```'

echo "✓ Issue #2 created"

gh issue create --repo "$REPO" \
  --title "feat: API Gateway with JWT auth and rate limiting" \
  --label "feat,priority:critical,milestone:foundation" \
  --body '## Issue #3: API Gateway with JWT auth and rate limiting

### Description
Build the FastAPI API gateway with JWT token validation (HS256), dev-token bypass for local development, token bucket rate limiter (60 req/min per user), CORS middleware, and routes for `/health`, `/ready`, `/api/v1/feed`, `/api/v1/users`.

### Files to create
```
services/api-gateway/src/main.py                    — FastAPI app with middleware
services/api-gateway/src/auth/jwt_handler.py         — JWT create/verify, TokenPayload model
services/api-gateway/src/middleware/rate_limiter.py   — TokenBucket + middleware
services/api-gateway/src/routes/feed.py              — GET /api/v1/feed
services/api-gateway/src/routes/users.py             — GET/POST /api/v1/users
services/api-gateway/src/routes/health.py            — GET /health, /ready
services/api-gateway/src/config/settings.py          — GatewaySettings (pydantic-settings)
services/api-gateway/Dockerfile
services/api-gateway/tests/unit/test_jwt.py
services/api-gateway/tests/unit/test_rate_limiter.py
services/api-gateway/tests/integration/test_gateway_endpoints.py
```

### Acceptance Criteria
- [ ] JWT create and verify with configurable secret (HS256)
- [ ] `dev-token` returns fixed user ID for local testing
- [ ] Token bucket rate limiter with `X-RateLimit-Remaining` header
- [ ] Health and readiness endpoints bypass rate limiting
- [ ] CORS middleware with configurable origins
- [ ] 3 unit tests for JWT (create+verify, dev-token, invalid)
- [ ] 5 unit tests for rate limiter (capacity, exhaustion, refill, cap)
- [ ] 5 integration tests for endpoints (health, ready, auth required, dev-token, rate-limit header)

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #3: Build API gateway with JWT handler, token bucket rate limiter, feed/users/health routes. Include all unit and integration tests."
git add -A && git commit -m "feat: api gateway with jwt auth and rate limiting (#3)"
```'

echo "✓ Issue #3 created"

gh issue create --repo "$REPO" \
  --title "feat: User Profile service with social graph" \
  --label "feat,priority:high,milestone:foundation" \
  --body '## Issue #4: User Profile service with social graph

### Description
Implement the user profile service with endpoints for `GET /users/{id}`, `GET /users/{id}/graph`, `GET /users/{id}/following`. In-memory store for dev, PostgreSQL-backed in production. Includes UserProfile and SocialGraph Pydantic models with content weights and muted authors.

### Files to create
```
services/user-profile/src/main.py           — FastAPI app with all endpoints + in-memory store
services/user-profile/Dockerfile
services/user-profile/tests/unit/test_profile.py
```

### Models
- `UserProfile`: user_id, username, display_name, bio, follower/following counts, content_weights dict, muted_authors list
- `SocialGraph`: user_id, following list, followers list, mutual_connections list
- `UserProfileStore`: async get_profile, get_graph, get_following_ids, upsert_profile, add_follow

### Acceptance Criteria
- [ ] GET `/users/{id}` returns UserProfile (404 if not found)
- [ ] GET `/users/{id}/graph` returns SocialGraph
- [ ] GET `/users/{id}/following` returns list of UUIDs
- [ ] `UserProfileStore` with in-memory dict backend
- [ ] Health endpoint at `/health`
- [ ] Dockerfile with uvicorn CMD on port 8003

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #4: Build user profile service with social graph endpoints, in-memory store, Pydantic models."
git add -A && git commit -m "feat: user profile service with social graph (#4)"
```'

echo "✓ Issue #4 created"

gh issue create --repo "$REPO" \
  --title "feat: Content Ingestion with Kafka consumers" \
  --label "feat,priority:high,milestone:foundation" \
  --body '## Issue #5: Content Ingestion with Kafka consumers

### Description
Build the engagement event consumer that processes likes, comments, shares from Kafka. Aggregates into windowed counters and detects engagement spikes (like >= 50/hr, comment >= 20/hr, share >= 10/hr) to trigger feed invalidation events.

### Files to create
```
services/content-ingestion/src/main.py
services/content-ingestion/src/consumers/engagement_consumer.py
services/content-ingestion/Dockerfile
services/content-ingestion/tests/unit/test_engagement_consumer.py
```

### Spike Thresholds
| Type | Threshold per hour |
|------|--------------------|
| like | 50 |
| comment | 20 |
| share | 10 |

### Acceptance Criteria
- [ ] `EngagementConsumer` class with `handle_event(event: dict)` method
- [ ] Windowed counter accumulation (total + window_1h)
- [ ] Spike detection with configurable thresholds per engagement type
- [ ] Malformed event handling (log warning and skip, do not crash)
- [ ] Feed invalidation emission on spike detection (placeholder/log)
- [ ] 4 unit tests: handle like, accumulate counts, malformed ignored, spike detection

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #5: Build engagement consumer with windowed counters, spike detection, malformed event handling. Include tests."
git add -A && git commit -m "feat: content ingestion with kafka consumers (#5)"
```'

echo "✓ Issue #5 created"

# ─── Milestone 2: Core Ranking Pipeline ───

gh issue create --repo "$REPO" \
  --title "feat: Feed Scorer with 6-feature weighted model" \
  --label "feat,priority:critical,milestone:core-pipeline" \
  --body '## Issue #6: Feed Scorer with 6-feature weighted model

### Description
Implement the feed scorer that computes relevance scores for candidate posts using 6 feature groups with configurable weights. Includes exponential recency decay function with half-life parameter. Batch scoring interface returns sorted ScoredPost list.

### Feature Groups and Weights
| Feature | Weight | Range | Formula |
|---------|--------|-------|---------|
| author_affinity | 0.25 | 0-1 | Past interaction frequency with author |
| engagement_velocity | 0.20 | 0-1 | `(likes + comments*2 + shares*3) / min(age_hours, 4) / 100` |
| recency_decay | 0.20 | 0-1 | `exp(-0.693 * age_hours / half_life)` where half_life=6h |
| content_type_pref | 0.15 | 0-1 | User preference weight for content type |
| social_proof | 0.10 | 0-1 | `mutual_engagement_count / 10` capped at 1.0 |
| post_quality | 0.10 | 0-1 | +0.3 base, +0.3 media, +0.2 text>50chars, +0.2 hashtags(1-5) |

### Files to create
```
services/feed-service/src/ranking/scorer.py
services/feed-service/src/models/post.py     — CandidatePost and ScoredPost
services/feed-service/tests/unit/test_scorer.py
```

### Acceptance Criteria
- [ ] `score_batch(candidates, preferences)` returns sorted `ScoredPost` list
- [ ] Recency decay: ~0.5 at half-life (6h), <0.01 at 48h
- [ ] Engagement velocity normalized to 0-1, capped
- [ ] Post quality accounts for media, text length, hashtag count
- [ ] Custom weights configurable via constructor
- [ ] 11 unit tests: sorted output, empty input, positive scores, recency near/far/half-life, velocity high/zero, quality rich/minimal, social proof cap, custom weights

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #6: Feed scorer with 6-feature groups (author_affinity, engagement_velocity, recency_decay, content_type_pref, social_proof, post_quality). Exponential decay half-life=6h. 11 unit tests."
git add -A && git commit -m "feat: feed scorer with weighted feature model (#6)"
```'

echo "✓ Issue #6 created"

gh issue create --repo "$REPO" \
  --title "feat: Feed Diversifier with business rules" \
  --label "feat,priority:critical,milestone:core-pipeline" \
  --body '## Issue #7: Feed Diversifier with business rules

### Description
Implement diversity rules that prevent monotonous feeds by constraining author frequency, ensuring media content presence, and interleaving trending posts at designated positions.

### Rules
1. **Author diversity**: Max 2 posts from the same author in any sliding window of 10
2. **Media diversity**: At least 1 image/video post in every window of 5
3. **Trending interleave**: Trending posts injected at positions 3, 8, 15
4. **Deferred posts**: Posts that violate author diversity are appended at end (not dropped)

### Files to create
```
services/feed-service/src/ranking/diversifier.py
services/feed-service/tests/unit/test_diversifier.py
```

### Acceptance Criteria
- [ ] Author diversity enforced with sliding window check
- [ ] Media diversity with swap-from-later strategy
- [ ] Trending interleave at designated positions (3, 8, 15)
- [ ] Preserves relative score ordering within constraints
- [ ] Empty input returns empty list
- [ ] 6 unit tests: empty, author diversity, multiple authors passthrough, trending interleave, score order preservation, single post

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #7: Feed diversifier with author cap (2 per 10), media diversity (1 per 5), trending interleave at positions 3/8/15. 6 unit tests."
git add -A && git commit -m "feat: feed diversifier with business rules (#7)"
```'

echo "✓ Issue #7 created"

gh issue create --repo "$REPO" \
  --title "feat: Feed Assembler with cursor pagination" \
  --label "feat,priority:critical,milestone:core-pipeline" \
  --body '## Issue #8: Feed Assembler with cursor pagination

### Description
Implement cursor-based pagination using base64-encoded offset cursors. Constructs FeedResponse with RankedPost items including sequential position tracking. Handles invalid and missing cursors gracefully.

### Cursor Format
```json
// Encoded as base64url
{"offset": 25}
```

### Files to create
```
services/feed-service/src/ranking/assembler.py
services/feed-service/src/models/feed.py      — FeedResponse and RankedPost
services/feed-service/tests/unit/test_assembler.py
```

### Acceptance Criteria
- [ ] base64 cursor encode/decode with offset payload
- [ ] Sequential position numbering across pages (page2 starts where page1 ended)
- [ ] `next_cursor` is None when at end of feed
- [ ] Invalid cursor resets to start (offset 0)
- [ ] `total_candidates` reflects full candidate pool size
- [ ] 7 unit tests: basic assembly, no next cursor at end, cursor pagination (2 pages), sequential positions, empty feed, invalid cursor, total candidates count

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #8: Feed assembler with base64 cursor pagination, position tracking, FeedResponse model. 7 unit tests."
git add -A && git commit -m "feat: feed assembler with cursor pagination (#8)"
```'

echo "✓ Issue #8 created"

gh issue create --repo "$REPO" \
  --title "feat: Feed Service orchestration endpoint" \
  --label "feat,priority:critical,milestone:core-pipeline" \
  --body '## Issue #9: Feed Service orchestration endpoint

### Description
Implement the core `GET /feed` endpoint that orchestrates the full ranking pipeline: check Redis cache, parallel fan-out for candidates (following + trending + preferences), deduplicate, score, diversify, assemble with pagination, cache result, and emit Kafka event. Cache key uses SHA256 hash of user_id + cursor.

### Pipeline
```
1. Cache check (Redis GET)      → HIT? return immediately
2. Parallel fan-out (asyncio.gather)
   ├── User Profile: preferences + follow graph
   ├── Content Ingestion: trending + explore candidates
   └── Redis: feature store data
3. Deduplicate by post_id
4. Score (call FeedScorer)
5. Diversify (call FeedDiversifier)
6. Assemble (call FeedAssembler with pagination)
7. Cache result (Redis SET, 300s TTL)
8. Emit feed-served event (Kafka async)
```

### Files to create
```
services/feed-service/src/main.py
services/feed-service/src/api/feed_handler.py
services/feed-service/src/cache/feed_cache.py
services/feed-service/tests/unit/test_cache.py
```

### Acceptance Criteria
- [ ] Cache-first pattern with SHA256 key and 300s TTL
- [ ] Parallel `asyncio.gather` for fan-out (3 concurrent calls)
- [ ] Deduplication by post_id using set
- [ ] Full pipeline: score → diversify → assemble → cache → emit
- [ ] Latency logging (cache hit vs cold path)
- [ ] `FeedCache` with in-memory dict fallback when Redis unavailable
- [ ] 4 cache unit tests: set+get, miss, invalidate, overwrite

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #9: Feed service orchestration endpoint with cache-first, parallel fan-out, dedup, score, diversify, assemble, cache, emit pipeline. FeedCache with in-memory fallback."
git add -A && git commit -m "feat: feed service orchestration endpoint (#9)"
```'

echo "✓ Issue #9 created"

gh issue create --repo "$REPO" \
  --title "feat: Ranking Engine with XGBoost model serving" \
  --label "feat,priority:high,milestone:core-pipeline" \
  --body '## Issue #10: Ranking Engine with XGBoost model serving

### Description
Build the ranking engine service with `POST /score` endpoint. Loads XGBoost model on startup (falls back to heuristic weighted sum when model file is absent). Supports A/B model variants via `model_version` parameter. Includes feature store client for windowed engagement aggregates (1h, 24h, 7d).

### Files to create
```
services/ranking-engine/src/main.py                   — FastAPI app + RankingModel class
services/ranking-engine/src/features/feature_store.py  — FeatureStore with windowed aggregates
services/ranking-engine/Dockerfile
services/ranking-engine/tests/unit/test_model.py
```

### API
```
POST /score
Body: { "candidates": [{"author_affinity": 0.8, ...}], "model_version": "v1" }
Response: { "scores": [0.73, 0.52, ...], "model_version": "v1" }
```

### Acceptance Criteria
- [ ] `POST /score` accepts batch feature dicts, returns float scores
- [ ] Heuristic fallback when model file missing (weighted sum with same weights as scorer)
- [ ] A/B variant via `model_version` parameter (defaults to "v1")
- [ ] `FeatureStore` with `get_post_features(post_id)` returning windowed counters
- [ ] `FeatureStore.update_features()` increments counters
- [ ] 5 unit tests: heuristic fallback, empty features, single candidate, unknown version, deterministic scores

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #10: Ranking engine with XGBoost model server, heuristic fallback, A/B variants, feature store with windowed aggregates. 5 unit tests."
git add -A && git commit -m "feat: ranking engine with xgboost serving (#10)"
```'

echo "✓ Issue #10 created"

# ─── Milestone 3: Infrastructure ───

gh issue create --repo "$REPO" \
  --title "infra: Docker Compose for full local dev stack" \
  --label "infra,priority:critical,milestone:infrastructure" \
  --body '## Issue #11: Docker Compose for full local dev stack

### Description
Create `docker-compose.yml` with all 5 application services, PostgreSQL 16, Redis 7, Kafka 3.7 (KRaft mode, no ZooKeeper), Jaeger (OTLP), Prometheus, and Grafana. Health checks on all infrastructure services. Shared YAML anchors for common environment variables. Individual Dockerfiles per service.

### Services and Ports
| Service | Port | Image |
|---------|------|-------|
| api-gateway | 8000 | Custom (Python 3.12-slim) |
| feed-service | 8001 | Custom |
| ranking-engine | 8002 | Custom |
| user-profile | 8003 | Custom |
| content-ingestion | 8004 | Custom |
| PostgreSQL | 5432 | postgres:16-alpine |
| Redis | 6379 | redis:7-alpine |
| Kafka | 9092 | bitnami/kafka:3.7 |
| Jaeger | 16686/4317 | jaegertracing/all-in-one:1.55 |
| Prometheus | 9090 | prom/prometheus:v2.50.0 |
| Grafana | 3000 | grafana/grafana:10.3.1 |

### Files to create
```
docker-compose.yml
docker/base-python.Dockerfile
docker/prometheus.yml
services/api-gateway/Dockerfile
services/feed-service/Dockerfile
services/ranking-engine/Dockerfile
.env.example
```

### Acceptance Criteria
- [ ] All services build and start with `docker compose up -d`
- [ ] Health checks on PostgreSQL (`pg_isready`), Redis (`redis-cli ping`), Kafka (`kafka-topics.sh --list`)
- [ ] Kafka in KRaft mode (no ZooKeeper dependency)
- [ ] `.env.example` with all configuration variables
- [ ] Jaeger UI on `:16686`, Grafana on `:3000`, Prometheus on `:9090`
- [ ] YAML anchors for shared env vars
- [ ] `restart: unless-stopped` on all services

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #11: docker-compose.yml with all services, PG, Redis, Kafka KRaft, Jaeger, Prometheus, Grafana. All Dockerfiles. .env.example."
git add -A && git commit -m "infra: docker compose for local dev stack (#11)"
```'

echo "✓ Issue #11 created"

gh issue create --repo "$REPO" \
  --title "ci: GitHub Actions CI/CD pipeline" \
  --label "ci,priority:critical,milestone:infrastructure" \
  --body '## Issue #12: GitHub Actions CI/CD pipeline

### Description
Multi-stage CI/CD pipeline: lint (ruff) → unit tests → integration tests (with PostgreSQL/Redis service containers) → Docker image build + push to GHCR → deploy to dev. Matrix build strategy for all 5 service Docker images.

### Files to create
```
.github/workflows/ci.yml
```

### Pipeline Stages
1. **Lint**: ruff check + ruff format --check
2. **Unit Tests**: pytest on all `tests/unit/` directories, JUnit XML output
3. **Integration Tests**: pytest with PG and Redis service containers
4. **Build Images**: matrix strategy for 5 services, push to ghcr.io with SHA + latest tags
5. **Deploy Dev**: kubectl apply (only on main branch)

### Acceptance Criteria
- [ ] Triggers on push to `main`/`develop`, PR to `main`
- [ ] Service containers for integration tests (PG + Redis)
- [ ] Matrix strategy for Docker builds across 5 services
- [ ] Push to `ghcr.io` with `${{ github.sha }}` and `latest` tags
- [ ] BuildX with GHA cache for fast rebuilds
- [ ] Deploy-dev job with kubectl (gated on main branch)
- [ ] Test results uploaded as artifact

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #12: .github/workflows/ci.yml with lint, unit test, integration test, Docker build matrix, deploy-dev stages."
git add -A && git commit -m "ci: github actions ci/cd pipeline (#12)"
```'

echo "✓ Issue #12 created"

gh issue create --repo "$REPO" \
  --title "infra: Kubernetes manifests with Kustomize overlays" \
  --label "infra,priority:high,milestone:infrastructure" \
  --body '## Issue #13: Kubernetes manifests with Kustomize overlays

### Description
Base Kubernetes deployment manifests for all services with readiness/liveness probes, resource requests/limits, and HPA. Kustomize overlays for dev (1 replica), staging, and production environments.

### Files to create
```
k8s/base/deployments.yaml
k8s/base/kustomization.yaml
k8s/overlays/dev/kustomization.yaml
k8s/overlays/staging/kustomization.yaml
k8s/overlays/prod/kustomization.yaml
```

### HPA Configuration
| Service | Min | Max | CPU Target | Memory Target |
|---------|-----|-----|------------|---------------|
| feed-service | 3 | 20 | 70% | 80% |
| ranking-engine | 2 | 10 | 60% | — |

### Acceptance Criteria
- [ ] Namespace `social-feed` with `istio-injection: enabled` label
- [ ] Deployments for all 5 services with correct image refs
- [ ] Resource requests and limits per service
- [ ] Readiness probe on `/health` (5s initial, 10s period)
- [ ] Liveness probe on `/health` (10s initial, 30s period)
- [ ] HPA for feed-service (3-20, CPU 70%, Mem 80%) and ranking-engine (2-10, CPU 60%)
- [ ] Dev overlay patches all replicas to 1

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #13: k8s/base/deployments.yaml with all services, HPA, probes. Kustomize overlays for dev/staging/prod."
git add -A && git commit -m "infra: kubernetes manifests with kustomize (#13)"
```'

echo "✓ Issue #13 created"

gh issue create --repo "$REPO" \
  --title "infra: Terraform EKS module" \
  --label "infra,priority:medium,milestone:infrastructure" \
  --body '## Issue #14: Terraform EKS module

### Description
Terraform module for AWS EKS cluster with managed node group, IAM roles with required policies, and configurable VPC/subnet variables.

### Files to create
```
terraform/modules/eks/main.tf
```

### Resources
- `aws_eks_cluster` with private + public endpoints
- `aws_eks_node_group` with t3.medium instances, scaling 2-10 nodes
- `aws_iam_role` for cluster (EKSClusterPolicy)
- `aws_iam_role` for nodes (WorkerNodePolicy, CNI, ECR)

### Acceptance Criteria
- [ ] EKS cluster resource with configurable name and region
- [ ] Managed node group with scaling config (min=2, max=10, desired=3)
- [ ] IAM roles with EKS, CNI, and ECR policy attachments
- [ ] Variables for cluster_name, region, instance_type, vpc_id, subnet_ids
- [ ] Outputs for cluster_endpoint and cluster_name
- [ ] Terraform >= 1.7, AWS provider ~> 5.0

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #14: terraform/modules/eks/main.tf with EKS cluster, managed node group, IAM roles."
git add -A && git commit -m "infra: terraform eks module (#14)"
```'

echo "✓ Issue #14 created"

gh issue create --repo "$REPO" \
  --title "infra: Observability stack integration" \
  --label "infra,priority:medium,milestone:infrastructure" \
  --body '## Issue #15: Observability stack integration

### Description
Prometheus scrape configuration for all services, OpenTelemetry integration in the shared logging module with OTLP gRPC exporter, and Jaeger collector setup.

### Files to create
```
docker/prometheus.yml                     — Scrape config for all 5 services
services/shared/src/utils/logging.py      — OTEL tracer factory (update)
```

### Acceptance Criteria
- [ ] `prometheus.yml` with scrape targets for all 5 service ports
- [ ] OTEL tracer factory creates `TracerProvider` with `OTLPSpanExporter` when `OTEL_EXPORTER_OTLP_ENDPOINT` is set
- [ ] Returns no-op tracer when OTEL is not configured
- [ ] Structured JSON logging with trace correlation IDs

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #15: Prometheus config, OTEL integration in shared logging, Jaeger setup."
git add -A && git commit -m "infra: observability stack integration (#15)"
```'

echo "✓ Issue #15 created"

# ─── Milestone 4: Hardening & Documentation ───

gh issue create --repo "$REPO" \
  --title "test: Integration test suite with test containers" \
  --label "test,priority:high,milestone:hardening" \
  --body '## Issue #16: Integration test suite with test containers

### Description
Create `docker-compose.test.yml` with isolated PostgreSQL, Redis, and Kafka instances pre-seeded with deterministic test data. Frozen test model for reproducible ranking scores. Integration tests that verify cross-service communication.

### Files to create
```
docker-compose.test.yml
tests/integration/test_feed_pipeline.py
tests/integration/conftest.py
```

### Acceptance Criteria
- [ ] Isolated infrastructure in `docker-compose.test.yml`
- [ ] Pre-seeded deterministic data (fixed UUIDs, fixed timestamps)
- [ ] Frozen XGBoost test model for reproducible scores
- [ ] End-to-end test: POST engagement → feed changes
- [ ] Cross-service health verification test

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #16: docker-compose.test.yml with isolated PG/Redis/Kafka, deterministic seed data, integration tests for feed pipeline."
git add -A && git commit -m "test: integration test suite with test containers (#16)"
```'

echo "✓ Issue #16 created"

gh issue create --repo "$REPO" \
  --title "test: Load testing with k6" \
  --label "test,priority:medium,milestone:hardening" \
  --body '## Issue #17: Load testing with k6

### Description
k6 load test scripts simulating concurrent feed requests. Measure p50/p95/p99 latency, throughput, and error rates against target SLOs.

### Files to create
```
tests/load/feed_load_test.js
tests/load/config.json
```

### SLO Targets
| Metric | Target |
|--------|--------|
| p50 latency (cached) | < 30ms |
| p99 latency (cold) | < 80ms |
| Error rate | < 0.1% |
| Throughput | > 1000 req/s |

### Acceptance Criteria
- [ ] k6 script with 1000 concurrent virtual users
- [ ] Ramp-up and steady-state phases
- [ ] Threshold checks against SLO targets
- [ ] JSON output for CI integration

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #17: k6 load test scripts with 1000 VUs, ramp-up, SLO thresholds (p50<30ms cached, p99<80ms cold)."
git add -A && git commit -m "test: load testing with k6 (#17)"
```'

echo "✓ Issue #17 created"

gh issue create --repo "$REPO" \
  --title "infra: Istio service mesh configuration" \
  --label "infra,priority:medium,milestone:hardening" \
  --body '## Issue #18: Istio service mesh configuration

### Description
Istio VirtualService and DestinationRule manifests for traffic management between services. mTLS enforcement, retry policies, and timeout configuration. Kiali dashboard deployment for mesh observability.

### Files to create
```
k8s/service-mesh/virtual-services.yaml
k8s/service-mesh/destination-rules.yaml
k8s/service-mesh/peer-authentication.yaml
k8s/kiali/kiali-deployment.yaml
```

### Acceptance Criteria
- [ ] VirtualService for each internal service with retry policy (3 attempts)
- [ ] DestinationRule with mTLS STRICT mode
- [ ] PeerAuthentication enforcing mTLS namespace-wide
- [ ] Timeout configuration (3s for ranking-engine, 5s for feed-service)
- [ ] Kiali deployment with port-forward instructions

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #18: Istio VirtualService/DestinationRule for all services, mTLS PeerAuthentication, Kiali deployment."
git add -A && git commit -m "infra: istio service mesh configuration (#18)"
```'

echo "✓ Issue #18 created"

gh issue create --repo "$REPO" \
  --title "docs: Architecture documentation and ADRs" \
  --label "docs,priority:high,milestone:hardening" \
  --body '## Issue #19: Architecture documentation and ADRs

### Description
Complete documentation package: C4 diagrams (system context, container, component for feed-service), session/sequence diagram with latency budget, all 6 ADRs, and comprehensive README with local setup, cloud deployment (Docker, EKS, GKE, AKS), and API reference.

### Files to create/update
```
README.md                                      — Full project README
docs/diagrams/architecture.md                  — C4 Level 1, 2, 3 + deployment diagram
docs/diagrams/session-flow.md                  — Request lifecycle with latency budget
docs/adr/001-kafka-event-streaming.md
docs/adr/002-redis-feed-caching.md
docs/adr/003-xgboost-ranking-model.md
docs/adr/004-postgres-data-store.md
docs/adr/005-fastapi-service-framework.md
docs/adr/006-istio-service-mesh.md
```

### ADR Format
Each ADR follows: Status → Context → Decision → Consequences (Positive/Negative/Mitigated)

### Acceptance Criteria
- [ ] C4 Level 1 (system context), Level 2 (container), Level 3 (feed-service components)
- [ ] Deployment architecture diagram (EKS + managed services)
- [ ] Session flow with all 7 stages and latency budget table
- [ ] Error handling documentation (Redis down, Ranking down, Kafka down, User Profile down)
- [ ] 6 ADRs with consistent format
- [ ] README: prerequisites, step-by-step local setup, Docker/cloud deployment, test commands

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #19: Full README.md, docs/diagrams/ with C4 and sequence diagrams, all 6 ADR files."
git add -A && git commit -m "docs: architecture documentation and adrs (#19)"
```'

echo "✓ Issue #19 created"

gh issue create --repo "$REPO" \
  --title "feat: Proto definitions for gRPC migration path" \
  --label "feat,priority:low,milestone:hardening" \
  --body '## Issue #20: Proto definitions for gRPC migration path

### Description
Protocol buffer definitions for internal service communication as a migration path from REST to gRPC. Defines messages and service RPCs for feed generation and engagement event streaming.

### Files to create
```
proto/feed.proto
proto/engagement.proto
```

### Proto Definitions

**feed.proto:**
- `FeedRequest`: user_id, cursor, limit
- `FeedResponse`: posts (repeated RankedPost), next_cursor, total_candidates
- `RankedPost`: post_id, author_id, content_type, score, position, timestamps
- `FeedService` RPC: `GetFeed(FeedRequest) returns (FeedResponse)`

**engagement.proto:**
- `EngagementEvent`: event_id, user_id, post_id, engagement_type, value, timestamp
- `ScoreRequest`: repeated FeatureVector
- `ScoreResponse`: repeated float scores, model_version
- `RankingService` RPC: `ScoreCandidates(ScoreRequest) returns (ScoreResponse)`

### Acceptance Criteria
- [ ] `feed.proto` with FeedService RPC definition
- [ ] `engagement.proto` with RankingService RPC definition
- [ ] Proto3 syntax with proper package naming
- [ ] Timestamp and UUID types handled correctly
- [ ] Comments documenting each message field

### Implementation Command
```bash
claude -p "Read skill/SKILL.md. Implement Issue #20: proto/feed.proto and proto/engagement.proto with FeedService and RankingService RPCs."
git add -A && git commit -m "feat: proto definitions for grpc migration path (#20)"
```'

echo "✓ Issue #20 created"

echo ""
echo "============================================"
echo "All 20 issues created successfully!"
echo "View them at: https://github.com/$REPO/issues"
echo "============================================"
