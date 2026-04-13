# GitHub Issues: Scalable Social Feed Ranking Service

All issues follow conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `ci:`, `infra:`

---

## Milestone 1: Foundation (Sprint 1)

### Issue #1: Project scaffolding and shared libraries
**Labels:** `feat`, `priority:critical`, `milestone:foundation`
**Description:**
Set up the monorepo structure with all service directories, shared libraries (Kafka client with circuit breaker, Redis client, structured logging, OpenTelemetry tracing), and Pydantic base models (PostEvent, EngagementEvent, FeedServedEvent, UserPreferences, PaginationCursor). Include pyproject.toml for each service.

**Acceptance Criteria:**
- [ ] All service directories created with src/ and tests/ structure
- [ ] Shared Kafka client with circuit breaker (CLOSED/OPEN/HALF_OPEN states)
- [ ] Shared Redis client with TTL management and circuit breaker
- [ ] Structured JSON logging with service name correlation
- [ ] OpenTelemetry tracer factory (no-op when unconfigured)
- [ ] Unit tests for circuit breaker (5 test cases)
- [ ] All __init__.py files present

---

### Issue #2: PostgreSQL schema and seed data
**Labels:** `feat`, `priority:critical`, `milestone:foundation`
**Description:**
Create the database schema with tables for users, posts, follows (social graph), engagement_events (append-only), user_preferences, and a materialized view for post_engagement_agg with windowed counters (1h, 24h). Add seed script generating 50 users, 500 posts, random follow graph, and 2000 engagement events.

**Acceptance Criteria:**
- [ ] init-db.sql with all tables, indexes, and materialized view
- [ ] UUID primary keys with uuid-ossp extension
- [ ] Proper indexes on posts(author_id), posts(created_at DESC), engagement_events(post_id)
- [ ] seed_data.py generates deterministic-ish sample data
- [ ] Script outputs to scripts/seed-data.json

---

### Issue #3: API Gateway with JWT auth and rate limiting
**Labels:** `feat`, `priority:critical`, `milestone:foundation`
**Description:**
Build the FastAPI API gateway with JWT token validation (HS256), dev-token bypass for local development, token bucket rate limiter (60 req/min per user), CORS middleware, and routes for /health, /ready, /api/v1/feed, /api/v1/users.

**Acceptance Criteria:**
- [ ] JWT create and verify with configurable secret
- [ ] dev-token returns fixed user ID for local testing
- [ ] Token bucket rate limiter with X-RateLimit-Remaining header
- [ ] Health and readiness endpoints bypass rate limiting
- [ ] 3 unit tests for JWT, 5 for rate limiter
- [ ] 5 integration tests for endpoints

---

### Issue #4: User Profile service with social graph
**Labels:** `feat`, `priority:high`, `milestone:foundation`
**Description:**
Implement the user profile service with endpoints for GET /users/{id}, GET /users/{id}/graph, GET /users/{id}/following. In-memory store for dev, PostgreSQL-backed in production. Includes UserProfile and SocialGraph Pydantic models.

**Acceptance Criteria:**
- [ ] GET profile, graph, and following endpoints
- [ ] UserProfile model with content_weights and muted_authors
- [ ] SocialGraph with following/followers/mutual_connections
- [ ] Health endpoint

---

### Issue #5: Content Ingestion with Kafka consumers
**Labels:** `feat`, `priority:high`, `milestone:foundation`
**Description:**
Build the engagement event consumer that processes likes, comments, shares from Kafka. Aggregates into windowed counters and detects engagement spikes (like >= 50/hr, comment >= 20/hr, share >= 10/hr) to trigger feed invalidation.

**Acceptance Criteria:**
- [ ] EngagementConsumer with handle_event method
- [ ] Windowed counter accumulation
- [ ] Spike detection with configurable thresholds
- [ ] Malformed event handling (log and skip)
- [ ] 4 unit tests

---

## Milestone 2: Core Ranking Pipeline (Sprint 2)

### Issue #6: Feed Scorer with 6-feature weighted model
**Labels:** `feat`, `priority:critical`, `milestone:core-pipeline`
**Description:**
Implement the feed scorer that computes relevance scores for candidate posts using 6 feature groups: author_affinity (0.25), engagement_velocity (0.20), recency_decay (0.20, half-life=6h), content_type_pref (0.15), social_proof (0.10), post_quality (0.10). Exponential decay function. Batch scoring interface.

**Acceptance Criteria:**
- [ ] score_batch returns sorted ScoredPost list
- [ ] Recency decay: 0.5 at half-life, <0.01 at 48h
- [ ] Engagement velocity normalized to 0-1
- [ ] Post quality accounts for media, text length, hashtags
- [ ] 11 unit tests covering all features and edge cases

---

### Issue #7: Feed Diversifier with business rules
**Labels:** `feat`, `priority:critical`, `milestone:core-pipeline`
**Description:**
Implement diversity rules: max 2 posts per author in window of 10, at least 1 image/video per window of 5, trending interleaved at positions 3/8/15, deferred posts appended at end.

**Acceptance Criteria:**
- [ ] Author diversity enforced with sliding window
- [ ] Media diversity with swap-from-later strategy
- [ ] Trending interleave at designated positions
- [ ] Preserves relative score ordering within constraints
- [ ] 6 unit tests

---

### Issue #8: Feed Assembler with cursor pagination
**Labels:** `feat`, `priority:critical`, `milestone:core-pipeline`
**Description:**
Implement cursor-based pagination using base64-encoded offset cursors. Constructs FeedResponse with RankedPost items including position tracking. Handles invalid/missing cursors gracefully.

**Acceptance Criteria:**
- [ ] base64 cursor encode/decode
- [ ] Sequential position numbering across pages
- [ ] next_cursor is None when at end
- [ ] Invalid cursor resets to start
- [ ] 7 unit tests

---

### Issue #9: Feed Service orchestration endpoint
**Labels:** `feat`, `priority:critical`, `milestone:core-pipeline`
**Description:**
Implement the core GET /feed endpoint that: checks Redis cache first, fans out parallel candidate retrieval (following + trending + preferences), deduplicates, scores, diversifies, assembles, caches result, and emits Kafka event. Cache key uses SHA256 hash of user_id + cursor.

**Acceptance Criteria:**
- [ ] Cache-first with 300s TTL
- [ ] Parallel asyncio.gather for fan-out
- [ ] Deduplication by post_id
- [ ] Full pipeline: score -> diversify -> assemble -> cache -> emit
- [ ] Latency logging
- [ ] FeedCache with in-memory fallback

---

### Issue #10: Ranking Engine with XGBoost model serving
**Labels:** `feat`, `priority:high`, `milestone:core-pipeline`
**Description:**
Build the ranking engine service with POST /score endpoint. Loads XGBoost model on startup (falls back to heuristic weighted sum). Supports A/B model variants. Includes feature store for windowed engagement aggregates.

**Acceptance Criteria:**
- [ ] POST /score accepts batch of feature dicts, returns scores
- [ ] Heuristic fallback when model file missing
- [ ] A/B variant via model_version parameter
- [ ] FeatureStore with 1h/24h/7d windows
- [ ] 5 unit tests for model, deterministic scoring

---

## Milestone 3: Infrastructure & DevOps (Sprint 3)

### Issue #11: Docker Compose for full local dev stack
**Labels:** `infra`, `priority:critical`, `milestone:infrastructure`
**Description:**
Create docker-compose.yml with all 5 services, PostgreSQL 16, Redis 7, Kafka 3.7 (KRaft mode), Jaeger, Prometheus, Grafana. Health checks on all infrastructure. Shared environment variable template.

**Acceptance Criteria:**
- [ ] All services build and start with `docker compose up -d`
- [ ] Health checks on PG, Redis, Kafka
- [ ] Kafka in KRaft mode (no ZooKeeper)
- [ ] .env.example with all configuration variables
- [ ] Jaeger UI on :16686, Grafana on :3000

---

### Issue #12: GitHub Actions CI/CD pipeline
**Labels:** `ci`, `priority:critical`, `milestone:infrastructure`
**Description:**
Multi-stage CI: lint (ruff) -> unit tests -> integration tests (with PG/Redis services) -> Docker image build + push to GHCR -> deploy to dev. Matrix build for all 5 service images.

**Acceptance Criteria:**
- [ ] Triggers on push to main/develop, PR to main
- [ ] Service containers for integration tests
- [ ] Matrix strategy for Docker builds
- [ ] Push to ghcr.io with SHA and latest tags
- [ ] Deploy-dev job with kubectl

---

### Issue #13: Kubernetes manifests with Kustomize
**Labels:** `infra`, `priority:high`, `milestone:infrastructure`
**Description:**
Base deployments for all services with readiness/liveness probes, resource limits, HPA on feed-service (3-20 replicas) and ranking-engine (2-10 replicas). Kustomize overlays for dev (1 replica), staging, prod.

**Acceptance Criteria:**
- [ ] Namespace social-feed with istio-injection label
- [ ] HPA targeting CPU 70% and memory 80%
- [ ] Dev overlay patches replicas to 1
- [ ] All services expose ClusterIP

---

### Issue #14: Terraform modules for AWS EKS
**Labels:** `infra`, `priority:medium`, `milestone:infrastructure`
**Description:**
Terraform module for EKS cluster with managed node group (t3.medium, 2-10 nodes), IAM roles for cluster and nodes, VPC/subnet variables.

**Acceptance Criteria:**
- [ ] EKS cluster resource with private + public endpoints
- [ ] Managed node group with scaling config
- [ ] IAM roles with EKS, CNI, and ECR policies
- [ ] Outputs for cluster endpoint and name

---

### Issue #15: Observability stack integration
**Labels:** `infra`, `priority:medium`, `milestone:infrastructure`
**Description:**
Prometheus scrape config for all services, Grafana dashboards, Jaeger OTLP collector, OpenTelemetry instrumentation in shared logging module.

**Acceptance Criteria:**
- [ ] prometheus.yml with service targets
- [ ] OTEL tracer factory with OTLP gRPC exporter
- [ ] Structured JSON logging with trace correlation

---

## Milestone 4: Hardening & Documentation (Sprint 4)

### Issue #16: Integration test suite with test containers
**Labels:** `test`, `priority:high`, `milestone:hardening`
**Description:**
docker-compose.test.yml with isolated PG, Redis, Kafka. Pre-seeded data for deterministic tests. Frozen test model for reproducible ranking scores.

---

### Issue #17: Load testing with k6
**Labels:** `test`, `priority:medium`, `milestone:hardening`
**Description:**
k6 scripts simulating 1000 concurrent feed requests. Measure p50/p95/p99 latency, throughput, error rate. Target: p99 < 80ms cold, < 50ms cached.

---

### Issue #18: Istio service mesh configuration
**Labels:** `infra`, `priority:medium`, `milestone:hardening`
**Description:**
Istio VirtualService and DestinationRule for traffic management. mTLS between services. Kiali dashboard for observability.

---

### Issue #19: Architecture documentation and ADRs
**Labels:** `docs`, `priority:high`, `milestone:hardening`
**Description:**
C4 diagrams (system context, container, component), session/sequence diagram, ADRs for Kafka, Redis, XGBoost, PostgreSQL, FastAPI, Istio decisions. Full README with local setup, cloud deployment, and API reference.

---

### Issue #20: Proto definitions for future gRPC migration
**Labels:** `feat`, `priority:low`, `milestone:hardening`
**Description:**
Protocol buffer definitions for feed.proto and engagement.proto as a migration path from REST to gRPC for internal service communication.

---

## Claude Code Implementation Commands

To implement each issue sequentially using Claude Code:

```bash
# Clone and enter repo
git clone https://github.com/AmosBunde/Scalable-Social-Feed-Ranking-Service.git
cd Scalable-Social-Feed-Ranking-Service

# Issue #1: Foundation
claude -p "Read the skill at skill/SKILL.md. Implement Issue #1: Create all shared libraries (kafka_client.py with circuit breaker, redis_client.py, logging.py, base models). Include all unit tests. Follow the exact file paths in the skill."
git add -A && git commit -m "feat: project scaffolding and shared libraries (#1)"

# Issue #2: Database
claude -p "Read skill/SKILL.md. Implement Issue #2: Create scripts/init-db.sql with full schema (users, posts, follows, engagement_events, materialized view, user_preferences) and scripts/seed_data.py."
git add -A && git commit -m "feat: postgresql schema and seed data (#2)"

# Issue #3: API Gateway
claude -p "Read skill/SKILL.md. Implement Issue #3: Build API gateway with JWT handler, token bucket rate limiter, feed/users/health routes. Include all unit and integration tests."
git add -A && git commit -m "feat: api gateway with jwt auth and rate limiting (#3)"

# Issue #4: User Profile
claude -p "Read skill/SKILL.md. Implement Issue #4: Build user profile service with social graph endpoints, in-memory store, Pydantic models."
git add -A && git commit -m "feat: user profile service with social graph (#4)"

# Issue #5: Content Ingestion
claude -p "Read skill/SKILL.md. Implement Issue #5: Build engagement consumer with windowed counters, spike detection, malformed event handling. Include tests."
git add -A && git commit -m "feat: content ingestion with kafka consumers (#5)"

# Issue #6: Scorer
claude -p "Read skill/SKILL.md. Implement Issue #6: Feed scorer with 6-feature groups (author_affinity, engagement_velocity, recency_decay, content_type_pref, social_proof, post_quality). Exponential decay half-life=6h. 11 unit tests."
git add -A && git commit -m "feat: feed scorer with weighted feature model (#6)"

# Issue #7: Diversifier
claude -p "Read skill/SKILL.md. Implement Issue #7: Feed diversifier with author cap (2 per 10), media diversity (1 per 5), trending interleave at positions 3/8/15. 6 unit tests."
git add -A && git commit -m "feat: feed diversifier with business rules (#7)"

# Issue #8: Assembler
claude -p "Read skill/SKILL.md. Implement Issue #8: Feed assembler with base64 cursor pagination, position tracking, FeedResponse model. 7 unit tests."
git add -A && git commit -m "feat: feed assembler with cursor pagination (#8)"

# Issue #9: Feed Service
claude -p "Read skill/SKILL.md. Implement Issue #9: Feed service orchestration endpoint with cache-first, parallel fan-out, dedup, score, diversify, assemble, cache, emit pipeline. FeedCache with in-memory fallback."
git add -A && git commit -m "feat: feed service orchestration endpoint (#9)"

# Issue #10: Ranking Engine
claude -p "Read skill/SKILL.md. Implement Issue #10: Ranking engine with XGBoost model server, heuristic fallback, A/B variants, feature store with windowed aggregates. 5 unit tests."
git add -A && git commit -m "feat: ranking engine with xgboost serving (#10)"

# Issue #11: Docker
claude -p "Read skill/SKILL.md. Implement Issue #11: docker-compose.yml with all services, PG, Redis, Kafka KRaft, Jaeger, Prometheus, Grafana. All Dockerfiles. .env.example."
git add -A && git commit -m "infra: docker compose for local dev stack (#11)"

# Issue #12: CI/CD
claude -p "Read skill/SKILL.md. Implement Issue #12: .github/workflows/ci.yml with lint, unit test, integration test, Docker build matrix, deploy-dev stages."
git add -A && git commit -m "ci: github actions ci/cd pipeline (#12)"

# Issue #13: Kubernetes
claude -p "Read skill/SKILL.md. Implement Issue #13: k8s/base/deployments.yaml with all services, HPA, probes. Kustomize overlays for dev/staging/prod."
git add -A && git commit -m "infra: kubernetes manifests with kustomize (#13)"

# Issue #14: Terraform
claude -p "Read skill/SKILL.md. Implement Issue #14: terraform/modules/eks/main.tf with EKS cluster, managed node group, IAM roles."
git add -A && git commit -m "infra: terraform eks module (#14)"

# Issue #15: Observability
claude -p "Read skill/SKILL.md. Implement Issue #15: Prometheus config, OTEL integration in shared logging, Jaeger setup."
git add -A && git commit -m "infra: observability stack integration (#15)"

# Issue #19: Documentation
claude -p "Read skill/SKILL.md. Implement Issue #19: Full README.md, docs/diagrams/ with C4 and sequence diagrams, all 6 ADR files."
git add -A && git commit -m "docs: architecture documentation and adrs (#19)"

# Push all
git push origin main
```
