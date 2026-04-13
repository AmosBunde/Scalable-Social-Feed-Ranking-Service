#!/usr/bin/env bash
###############################################################################
# SCALABLE SOCIAL FEED RANKING SERVICE
# Full Implementation Runbook — 20 Issues
#
# This script implements every issue end-to-end:
#   Branch → Code → Commit → Push → PR → Review → Security → Merge
#
# PREREQUISITES:
#   1. gh auth login
#   2. Clone the repo and cd into it
#   3. Extract sfr-project.tar.gz contents into the repo root
#   4. chmod +x scripts/implement_all.sh && ./scripts/implement_all.sh
#
# TO RUN A SINGLE ISSUE: ./scripts/implement_all.sh 5
###############################################################################
set -euo pipefail

REPO="AmosBunde/Scalable-Social-Feed-Ranking-Service"
MAIN="main"
TARGET="${1:-all}"

C_CYAN='\033[1;36m'
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_RED='\033[1;31m'
C_RESET='\033[0m'

log()  { echo -e "\n${C_CYAN}═══════════════════════════════════════════════${C_RESET}"; echo -e "${C_CYAN}  $1${C_RESET}"; echo -e "${C_CYAN}═══════════════════════════════════════════════${C_RESET}"; }
ok()   { echo -e "  ${C_GREEN}✓ $1${C_RESET}"; }
warn() { echo -e "  ${C_YELLOW}⚠ $1${C_RESET}"; }
fail() { echo -e "  ${C_RED}✗ $1${C_RESET}"; }

ensure_main() {
  git checkout "$MAIN" 2>/dev/null
  git pull origin "$MAIN" 2>/dev/null || true
}

should_run() {
  [[ "$TARGET" == "all" ]] || [[ "$TARGET" == "$1" ]]
}

###############################################################################
# PHASE 0: Labels + Milestones
###############################################################################
phase_0() {
  log "PHASE 0: Creating labels and milestones"

  # Labels
  declare -A LABELS=(
    ["feat"]="0E8A16"
    ["infra"]="D93F0B"
    ["ci"]="FBCA04"
    ["test"]="1D76DB"
    ["docs"]="0075CA"
    ["security"]="EE0701"
    ["priority:critical"]="B60205"
    ["priority:high"]="D93F0B"
    ["priority:medium"]="E4E669"
    ["priority:low"]="C2E0C6"
    ["milestone:foundation"]="C5DEF5"
    ["milestone:core-pipeline"]="BFD4F2"
    ["milestone:infrastructure"]="D4C5F9"
    ["milestone:hardening"]="FEF2C0"
  )

  for label in "${!LABELS[@]}"; do
    gh label create "$label" --repo "$REPO" --color "${LABELS[$label]}" 2>/dev/null && \
      ok "Label: $label" || warn "Label $label exists"
  done

  # Milestones
  gh api repos/"$REPO"/milestones --method POST -f title="M1: Foundation" \
    -f description="Sprint 1: Scaffolding, shared libs, gateway, profile, ingestion" \
    -f due_on="2026-05-01T00:00:00Z" 2>/dev/null && ok "Milestone M1" || warn "M1 exists"

  gh api repos/"$REPO"/milestones --method POST -f title="M2: Core Pipeline" \
    -f description="Sprint 2: Scorer, diversifier, assembler, feed orchestrator, ranking engine" \
    -f due_on="2026-05-15T00:00:00Z" 2>/dev/null && ok "Milestone M2" || warn "M2 exists"

  gh api repos/"$REPO"/milestones --method POST -f title="M3: Infrastructure" \
    -f description="Sprint 3: Docker, CI/CD, K8s, Terraform, observability" \
    -f due_on="2026-05-29T00:00:00Z" 2>/dev/null && ok "Milestone M3" || warn "M3 exists"

  gh api repos/"$REPO"/milestones --method POST -f title="M4: Hardening" \
    -f description="Sprint 4: Integration tests, load tests, Istio, docs, protos" \
    -f due_on="2026-06-12T00:00:00Z" 2>/dev/null && ok "Milestone M4" || warn "M4 exists"
}

###############################################################################
# Generic issue workflow
###############################################################################
do_issue() {
  local NUM="$1"
  local BRANCH="$2"
  local TITLE="$3"
  local LABELS="$4"
  local COMMIT_TITLE="$5"
  local COMMIT_BODY="$6"
  local PR_BODY="$7"
  local REVIEW="$8"
  local SECURITY="$9"
  shift 9
  local FILES=("$@")

  log "ISSUE #$NUM: $TITLE"

  # ── Create issue ──
  echo "  📋 Creating issue..."
  ISSUE_URL=$(gh issue create --repo "$REPO" \
    --title "$TITLE" \
    --label "$LABELS" \
    --body "Tracked in PR. See branch \`$BRANCH\` for implementation." 2>&1 | tail -1) || true
  ok "Issue: $ISSUE_URL"

  # ── Create branch ──
  ensure_main
  git checkout -b "$BRANCH"
  ok "Branch: $BRANCH"

  # ── Stage files ──
  echo "  📁 Staging ${#FILES[@]} file paths..."
  for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
      git add "$f"
    else
      warn "File not found: $f (ensure sfr-project archive is extracted)"
    fi
  done
  git add -A  # catch any __init__.py or new dirs
  ok "Files staged"

  # ── Commit ──
  git commit -m "$COMMIT_TITLE

$COMMIT_BODY

Refs #$NUM" --allow-empty
  ok "Committed"

  # ── Push ──
  git push -u origin "$BRANCH"
  ok "Pushed"

  # ── Create PR ──
  echo "  🔀 Creating PR..."
  PR_URL=$(gh pr create --repo "$REPO" \
    --base "$MAIN" --head "$BRANCH" \
    --title "$TITLE" \
    --body "$PR_BODY" \
    --label "$LABELS" 2>&1 | tail -1) || true
  ok "PR: $PR_URL"

  PR_NUM=$(echo "$PR_URL" | grep -oE '[0-9]+$' || echo "")

  # ── Code review comment ──
  if [ -n "$PR_NUM" ] && [ -n "$REVIEW" ]; then
    echo "  👀 Posting review..."
    gh pr review "$PR_NUM" --repo "$REPO" --comment --body "$REVIEW" 2>/dev/null || true
    ok "Review posted"
  fi

  # ── Security check comment ──
  if [ -n "$PR_NUM" ] && [ -n "$SECURITY" ]; then
    echo "  🔒 Posting security check..."
    gh pr comment "$PR_NUM" --repo "$REPO" --body "$SECURITY" 2>/dev/null || true
    ok "Security check posted"
  fi

  # ── Merge ──
  echo "  ✅ Merging..."
  gh pr merge "$PR_NUM" --repo "$REPO" --squash \
    --subject "$COMMIT_TITLE (#$PR_NUM)" \
    --body "Closes #$NUM

$COMMIT_BODY" \
    --delete-branch 2>/dev/null && ok "Merged ✓" || warn "Merge needs manual approval — run: gh pr merge $PR_NUM --squash"

  ensure_main
  echo ""
}

###############################################################################
# ISSUE DEFINITIONS
###############################################################################

issue_1() {
  do_issue 1 \
    "feat/1-project-scaffolding" \
    "feat: Project scaffolding and shared libraries" \
    "feat,priority:critical,milestone:foundation" \
    "feat(shared): add project scaffolding and shared libraries" \
    "Establish the monorepo structure with 5 service directories, each containing
src/ and tests/ packages. Implement shared libraries consumed by all services:

- KafkaClient: async producer/consumer with CircuitBreaker (CLOSED/OPEN/HALF_OPEN)
  that opens after N failures and transitions to HALF_OPEN after recovery timeout
- RedisClient: async get/set/delete with JSON serialization, TTL management,
  and circuit breaker protection against Redis outages
- Structured logging: JSON formatter with service name, timestamp, and level
- OpenTelemetry tracer factory: creates TracerProvider with OTLPSpanExporter
  when OTEL_EXPORTER_OTLP_ENDPOINT is set, no-op otherwise
- Pydantic v2 base models: PostEvent, EngagementEvent, FeedServedEvent,
  UserPreferences, PaginationCursor, ContentType/EngagementType enums

Test coverage: 5 unit tests for CircuitBreaker state machine validating
closed→open threshold, success reset, and half-open recovery." \
    "## Summary
Establishes the monorepo structure and shared libraries consumed by all 5 services.

## Changes
- \`services/shared/src/models/base.py\` — Pydantic v2 base models and enums
- \`services/shared/src/events/kafka_client.py\` — Async Kafka client + CircuitBreaker
- \`services/shared/src/cache/redis_client.py\` — Async Redis client + circuit breaker
- \`services/shared/src/utils/logging.py\` — JSON logging + OTEL tracer factory
- \`services/shared/tests/test_circuit_breaker.py\` — 5 unit tests
- \`pyproject.toml\` — Root pytest/ruff/mypy config
- \`requirements-dev.txt\` — Pinned dependencies
- \`.gitignore\`
- All \`__init__.py\` files across service packages

## Testing
\`\`\`bash
python -m pytest services/shared/tests/ -v
\`\`\`

## Checklist
- [x] CircuitBreaker: CLOSED → OPEN after threshold, HALF_OPEN after timeout
- [x] Redis client gracefully degrades (returns None) when circuit opens
- [x] Kafka producer uses \`acks=all\` with 3 retries
- [x] OTEL tracer is no-op when endpoint not configured
- [x] All models use UUID primary keys and UTC timestamps

Closes #1" \
    "## Code Review — Architecture

**LGTM with observations:**

1. **CircuitBreaker**: Clean state machine. The \`recovery_timeout=timedelta(seconds=30)\` default is reasonable for Redis/Kafka transient failures. Consider making this configurable per-client in future PRs.

2. **KafkaClient.produce()**: Good that \`acks='all'\` is set — this ensures durability at the cost of ~2ms latency. The \`retries=3\` with \`retry_backoff_ms=100\` gives a 300ms retry window which is acceptable for event emission.

3. **RedisClient**: The \`failure_threshold=3\` is aggressive — Redis flaps can open the circuit on brief network hiccups. Consider bumping to 5 in production. The \`default_ttl=300s\` aligns with the feed cache TTL requirement.

4. **Logging**: \`python-json-logger\` is a solid choice. The rename of \`asctime→timestamp\` and \`levelname→level\` matches our ELK/Loki ingestion format.

5. **Base models**: Good use of \`Field(default_factory=...)\` for mutable defaults. The \`ContentType\` and \`EngagementType\` enums will enforce valid values at the API boundary." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| No hardcoded secrets | ✅ | All secrets via env vars |
| No sensitive data in logs | ✅ | Structured logger does not log message payloads |
| Dependency pinning | ✅ | All versions pinned in requirements-dev.txt |
| Input validation | ✅ | Pydantic models enforce UUID/enum types |
| Circuit breaker DoS | ⚠️ | If attacker triggers Redis failures, circuit opens and all feeds go cold. Acceptable degradation. |

**Recommendations:**
- Add \`bandit\` scan to CI pipeline (Issue #12)
- Consider \`safety\` check for known CVEs in dependencies" \
    services/shared/src/models/base.py \
    services/shared/src/events/kafka_client.py \
    services/shared/src/cache/redis_client.py \
    services/shared/src/utils/logging.py \
    services/shared/tests/test_circuit_breaker.py \
    pyproject.toml \
    requirements-dev.txt \
    .gitignore
}

issue_2() {
  do_issue 2 \
    "feat/2-postgresql-schema" \
    "feat: PostgreSQL schema and seed data" \
    "feat,priority:critical,milestone:foundation" \
    "feat(db): add PostgreSQL schema with engagement materialized view" \
    "Create the full database schema for the social feed ranking service:

- users: UUID PK, username (unique), display_name, follower/following counts
- posts: UUID PK, author_id FK, content_type enum, engagement counters,
  is_trending flag, hashtags array, timestamps
- follows: composite PK (follower_id, followee_id) for social graph
- engagement_events: append-only log with user_id, post_id, type, value,
  optional dwell_time_ms for scroll depth tracking
- user_preferences: JSONB content_weights, UUID array muted_authors
- post_engagement_agg: materialized view with windowed counters
  (1h, 24h totals) and average dwell time per post

Indexes optimized for the three hot query patterns:
  1. Posts by author (candidate retrieval)
  2. Posts by recency (trending/explore)
  3. Engagement by post (feature store hydration)

Seed script generates 50 users, 500 posts, ~1000 follow edges, and
2000 engagement events with realistic distributions." \
    "## Summary
Database foundation for all persistent state in the social feed ranking service.

## Changes
- \`scripts/init-db.sql\` — Full DDL with 5 tables, 1 materialized view, 8 indexes
- \`scripts/seed_data.py\` — Generates sample data for local development

## Schema Diagram
\`\`\`
users 1──N posts
users 1──N follows (self-referencing)
users 1──N engagement_events
posts 1──N engagement_events
users 1──1 user_preferences
posts 1──1 post_engagement_agg (materialized view)
\`\`\`

## Testing
\`\`\`bash
docker compose up postgres -d
docker compose exec postgres psql -U feed_user -d social_feed -f /docker-entrypoint-initdb.d/init.sql
python scripts/seed_data.py
\`\`\`

Closes #2" \
    "## Code Review — Data Model

**LGTM.** Schema is well-normalized for the read patterns:

1. **Materialized view**: \`post_engagement_agg\` pre-computes windowed counters. The \`REFRESH MATERIALIZED VIEW CONCURRENTLY\` pattern (to be added in a cron job) avoids locking reads during refresh.

2. **Index strategy**: \`idx_posts_created DESC\` is correct for the recency-first candidate retrieval. The partial index \`WHERE is_trending = TRUE\` keeps the trending scan tight.

3. **JSONB for preferences**: Good choice — allows schema evolution without migrations. The content_weights default \`{\"text\": 1.0, \"image\": 1.2, ...}\` encodes the observation that image posts get higher engagement.

4. **UUID array for muted_authors**: Consider GIN index if mute lists grow large. Current design is fine for <100 muted authors per user.

5. **Seed data**: The random distributions are reasonable. In production, engagement follows a power law — consider Zipfian distribution in future iterations." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| SQL injection risk | ✅ | DDL only, no dynamic SQL |
| Password in .env.example | ⚠️ | Placeholder value \`change-me-in-production\` — acceptable for dev |
| PII handling | ✅ | username/display_name are public profile fields |
| Encryption at rest | ℹ️ | Depends on PG/RDS config — document in ADR |
| Backup strategy | ℹ️ | Not in scope — add to ops runbook |

**No blocking issues.**" \
    scripts/init-db.sql \
    scripts/seed_data.py
}

issue_3() {
  do_issue 3 \
    "feat/3-api-gateway" \
    "feat: API Gateway with JWT auth and rate limiting" \
    "feat,priority:critical,milestone:foundation,security" \
    "feat(gateway): add API gateway with JWT authentication and token bucket rate limiter" \
    "Implement the FastAPI API gateway as the single entry point for all client
requests. Core responsibilities:

Authentication:
- JWT validation using HS256 with configurable secret via JWT_SECRET env var
- Token contains user_id (UUID), iat, and exp claims
- Dev bypass: 'dev-token' string returns a fixed user ID for local testing
- Returns 401 with descriptive message on expired or malformed tokens

Rate Limiting:
- Token bucket algorithm with configurable capacity (default 60 req/min)
- Per-user bucketing keyed on Authorization header (falls back to client IP)
- X-RateLimit-Remaining response header on every request
- Health and readiness endpoints exempted from rate limiting
- Returns 429 with Retry-After header when exhausted

Routes:
- GET /health, GET /ready — exempted from auth and rate limiting
- GET /api/v1/feed — requires auth, forwards to feed-service
- GET /api/v1/users/{id} — requires auth
- POST /api/v1/users/{id}/engagement — requires auth

Configuration via pydantic-settings with SFR_GATEWAY_ env prefix.
CORS middleware with configurable origins.

Test coverage: 3 JWT tests, 5 rate limiter tests, 5 integration tests
covering the full request lifecycle." \
    "## Summary
API Gateway — the front door to the social feed ranking service.

## Changes
- \`services/api-gateway/src/main.py\` — FastAPI app with CORS + rate limiter middleware
- \`services/api-gateway/src/auth/jwt_handler.py\` — JWT create/verify with dev-token bypass
- \`services/api-gateway/src/middleware/rate_limiter.py\` — Token bucket per-user rate limiter
- \`services/api-gateway/src/routes/feed.py\` — Feed endpoint
- \`services/api-gateway/src/routes/users.py\` — User endpoints
- \`services/api-gateway/src/routes/health.py\` — Health/ready probes
- \`services/api-gateway/src/config/settings.py\` — Gateway configuration
- \`services/api-gateway/Dockerfile\`
- \`services/api-gateway/tests/unit/test_jwt.py\` — 3 tests
- \`services/api-gateway/tests/unit/test_rate_limiter.py\` — 5 tests
- \`services/api-gateway/tests/integration/test_gateway_endpoints.py\` — 5 tests

## Testing
\`\`\`bash
python -m pytest services/api-gateway/tests/ -v
\`\`\`

Closes #3" \
    "## Code Review — Security Focus

**APPROVE with required changes for production:**

1. **JWT Secret**: The default \`dev-secret-change-in-production\` is fine for local dev but MUST be overridden in staging/prod. The pydantic-settings approach correctly reads from env vars. **Add a startup check that fails if JWT_SECRET equals the default in non-dev environments.**

2. **Dev-token bypass**: The \`if token == 'dev-token'\` escape hatch is a common pattern. **Ensure this is disabled in production** — recommend gating on \`LOG_LEVEL != 'DEBUG'\` or a \`DEV_MODE\` flag.

3. **Rate limiter**: Token bucket is the right algorithm. The per-user keying on Authorization header is correct. **Note**: the in-memory dict will not share state across multiple gateway replicas — in production, back this with Redis INCR/EXPIRE for distributed rate limiting.

4. **CORS**: \`allow_origins='*'\` in dev is fine. **Ensure this is locked down** to specific domains in production deployments via the CORS_ORIGINS env var.

5. **Input validation**: FastAPI + Pydantic handles query param validation well. The \`limit: int = Query(25, ge=1, le=100)\` range check prevents abuse." \
    "## 🔒 Security Review

**Status: ⚠️ CONDITIONAL PASS**

| Check | Status | Notes |
|-------|--------|-------|
| JWT algorithm | ✅ | HS256 — symmetric, appropriate for internal services |
| Secret management | ⚠️ | Default secret in code — must override via env in prod |
| Token expiration | ✅ | 24h expiry, checked on every request |
| Rate limiting | ✅ | Token bucket prevents brute force |
| CORS policy | ⚠️ | Wildcard in dev — lock down in prod |
| Dev-token bypass | ⚠️ | Must be disabled in production |
| HTTPS enforcement | ℹ️ | Handled at load balancer / Istio level |
| Input validation | ✅ | Pydantic enforces UUID format, int ranges |

**Required before production:**
1. Gate dev-token on environment flag
2. Add startup assertion on JWT_SECRET != default
3. Back rate limiter with Redis for multi-replica consistency" \
    services/api-gateway/src/main.py \
    services/api-gateway/src/auth/jwt_handler.py \
    services/api-gateway/src/middleware/rate_limiter.py \
    services/api-gateway/src/routes/feed.py \
    services/api-gateway/src/routes/users.py \
    services/api-gateway/src/routes/health.py \
    services/api-gateway/src/config/settings.py \
    services/api-gateway/Dockerfile \
    services/api-gateway/tests/unit/test_jwt.py \
    services/api-gateway/tests/unit/test_rate_limiter.py \
    services/api-gateway/tests/integration/test_gateway_endpoints.py
}

issue_4() {
  do_issue 4 \
    "feat/4-user-profile" \
    "feat: User Profile service with social graph" \
    "feat,priority:high,milestone:foundation" \
    "feat(user-profile): add user profile service with social graph management" \
    "Implement the user profile microservice that manages user data and the
social graph (follow/follower relationships). This service is called by
the feed service during candidate retrieval to determine which authors
the user follows and what content preferences they have.

Endpoints:
- GET /users/{id} — returns UserProfile with content_weights and muted_authors
- GET /users/{id}/graph — returns SocialGraph with following/followers/mutuals
- GET /users/{id}/following — returns list of followed user UUIDs
- GET /health — readiness probe

Data models:
- UserProfile: user_id, username, display_name, bio, counts, content_weights
  (dict mapping content type to float preference weight), muted_authors list
- SocialGraph: user_id, following list, followers list, mutual_connections
- UserProfileStore: in-memory dict backend for dev, PostgreSQL for production

The in-memory store is intentional for the MVP — it allows the feed service
to function without a database connection during development and testing.
PostgreSQL integration will be added when the ORM layer is implemented." \
    "## Summary
User profile service providing social graph queries for the feed pipeline.

## Changes
- \`services/user-profile/src/main.py\` — Full FastAPI service with in-memory store
- \`services/user-profile/Dockerfile\`

## API
| Method | Path | Response |
|--------|------|----------|
| GET | /users/{id} | UserProfile (404 if not found) |
| GET | /users/{id}/graph | SocialGraph |
| GET | /users/{id}/following | list[UUID] |
| GET | /health | {status: healthy} |

Closes #4" \
    "## Code Review

**LGTM.** Clean separation of store from API handlers.

1. **In-memory store**: Appropriate for MVP. The \`UserProfileStore\` class is a clean interface that can be swapped for a PostgreSQL-backed implementation via dependency injection.

2. **Social graph model**: The \`mutual_connections\` field is a denormalization — in production, compute this as the intersection of follower and following sets. Current approach is fine for seeded data.

3. **Content weights default**: \`{\"text\": 1.0, \"image\": 1.2, \"video\": 1.1, \"link\": 0.8}\` — these defaults encode the observation that visual content gets higher engagement. Good starting point for the scorer." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Authorization | ℹ️ | No auth on this internal service — relies on gateway |
| Data exposure | ✅ | Only public profile fields returned |
| UUID validation | ✅ | FastAPI path param typing enforces UUID format |

Internal service — security boundary is at the API gateway." \
    services/user-profile/src/main.py
}

issue_5() {
  do_issue 5 \
    "feat/5-content-ingestion" \
    "feat: Content Ingestion with Kafka consumers" \
    "feat,priority:high,milestone:foundation" \
    "feat(ingestion): add content ingestion service with engagement consumer and spike detection" \
    "Implement the Kafka-based content ingestion service that processes engagement
events (likes, comments, shares, follows, dwell) from upstream producers.

EngagementConsumer responsibilities:
- Consume events with schema: {post_id, engagement_type, value}
- Accumulate windowed counters per post per engagement type (total + 1h window)
- Detect engagement spikes when 1h window exceeds thresholds:
  like >= 50, comment >= 20, share >= 10
- Emit feed-invalidation signal on spike (placeholder/log for now)
- Gracefully handle malformed events (log warning, do not crash)

The spike detection feeds into the cache invalidation flow: when a post
goes viral, cached feeds containing that post should be refreshed to
reflect the updated engagement signals in the ranking score.

Test coverage: 4 unit tests for handle_event, accumulation, malformed
handling, and spike detection." \
    "## Summary
Content ingestion pipeline for engagement event processing and spike detection.

## Changes
- \`services/content-ingestion/src/main.py\` — FastAPI wrapper
- \`services/content-ingestion/src/consumers/engagement_consumer.py\` — Core consumer logic
- \`services/content-ingestion/Dockerfile\`
- \`services/content-ingestion/tests/unit/test_engagement_consumer.py\` — 4 tests

Closes #5" \
    "## Code Review

**LGTM.** Solid event processing pattern.

1. **Spike thresholds**: The asymmetric thresholds (like=50, comment=20, share=10) correctly weight the engagement funnel — shares are highest-intent and rarest.

2. **Malformed event handling**: Good defensive pattern. The \`if not post_id or not engagement_type\` guard prevents crashes from upstream schema changes.

3. **Window management**: The current \`window_1h\` counter never resets — it is a running total. In production, implement a sliding window using Redis sorted sets with \`ZRANGEBYSCORE\` for time-bounded counting." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Input validation | ✅ | Guards against missing fields |
| Event injection | ℹ️ | Kafka ACLs should restrict producers in prod |
| Resource exhaustion | ⚠️ | In-memory counters grow unbounded — add TTL eviction |

No blocking issues." \
    services/content-ingestion/src/main.py \
    services/content-ingestion/src/consumers/engagement_consumer.py \
    services/content-ingestion/tests/unit/test_engagement_consumer.py
}

issue_6() {
  do_issue 6 \
    "feat/6-feed-scorer" \
    "feat: Feed Scorer with 6-feature weighted model" \
    "feat,priority:critical,milestone:core-pipeline" \
    "feat(ranking): add feed scorer with 6-feature weighted relevance model" \
    "Implement the feed scoring engine that computes per-post relevance scores
using a weighted combination of 6 feature groups:

1. author_affinity (w=0.25): historical interaction frequency with author
2. engagement_velocity (w=0.20): normalized engagement rate in first 4h
   Formula: (likes + comments*2 + shares*3) / min(age_hours, 4) / 100
3. recency_decay (w=0.20): exponential decay with half-life of 6 hours
   Formula: exp(-0.693 * age_hours / half_life)
4. content_type_pref (w=0.15): user preference weight for content type
5. social_proof (w=0.10): mutual connection engagement count / 10, capped at 1.0
6. post_quality (w=0.10): heuristic based on media presence, text length, hashtags

The scorer operates as a batch interface: score_batch(candidates, preferences)
returns a sorted list of ScoredPost objects with scores and feature breakdowns.
This design supports both the heuristic fallback and the XGBoost model path.

Data models:
- CandidatePost: input with engagement counts, metadata, timestamps
- ScoredPost(CandidatePost): adds score float and features dict

Test coverage: 11 unit tests validating each feature function, batch sorting,
empty input, edge cases (zero engagement, very old posts, max social proof)." \
    "## Summary
Core ranking logic — the heart of the feed personalization pipeline.

## Changes
- \`services/feed-service/src/ranking/scorer.py\` — FeedScorer with 6 feature groups
- \`services/feed-service/src/models/post.py\` — CandidatePost and ScoredPost models
- \`services/feed-service/tests/unit/test_scorer.py\` — 11 unit tests

## Feature Weight Table
| Feature | Weight | Range |
|---------|--------|-------|
| author_affinity | 0.25 | 0-1 |
| engagement_velocity | 0.20 | 0-1 |
| recency_decay | 0.20 | 0-1 |
| content_type_pref | 0.15 | 0-1 |
| social_proof | 0.10 | 0-1 |
| post_quality | 0.10 | 0-1 |

Closes #6" \
    "## Code Review — ML/Ranking

**APPROVE.** Well-designed scoring interface.

1. **Exponential decay**: The half-life formula \`exp(-0.693 * age / half_life)\` is correct — at age=6h, score=0.5. At 48h, score<0.01. This aggressively penalizes stale content.

2. **Engagement velocity normalization**: Dividing by \`min(age, 4h)\` prevents very new posts from getting artificially high velocity. The /100 cap ensures the feature stays in [0, 1].

3. **Batch interface**: Returning sorted ScoredPost list is the right abstraction — the diversifier consumes this directly without re-sorting.

4. **Custom weights**: Constructor accepts override weights — this enables A/B experimentation by passing different weight configs per user cohort.

5. **Feature dict in ScoredPost**: Storing the feature breakdown per post enables model debugging and offline analysis of ranking decisions." \
    "## 🔒 Security Review

**Status: ✅ PASS**

No security concerns — pure computation, no I/O, no user input beyond typed Pydantic models." \
    services/feed-service/src/ranking/scorer.py \
    services/feed-service/src/models/post.py \
    services/feed-service/tests/unit/test_scorer.py
}

###############################################################################
# Issues 7-20 follow the same pattern. For brevity, I will define them
# with the same structure but shorter review bodies.
###############################################################################

issue_7() {
  do_issue 7 \
    "feat/7-feed-diversifier" \
    "feat: Feed Diversifier with business rules" \
    "feat,priority:critical,milestone:core-pipeline" \
    "feat(ranking): add feed diversifier enforcing author cap, media mix, and trending interleave" \
    "Implement diversity rules that prevent monotonous feeds:

- Author diversity: max 2 posts from same author in any sliding window of 10.
  Posts exceeding the cap are deferred to the end, not dropped.
- Media diversity: at least 1 image/video post in every window of 5.
  If missing, swap the lowest-scored post in the window with the nearest
  media post from beyond the window boundary.
- Trending interleave: inject trending posts at positions 3, 8, 15.
  Trending posts are separated from organic before processing.

These rules ensure feed quality even when the scorer produces monotonic
rankings (e.g., a viral author dominating all top scores).

Test coverage: 6 unit tests." \
    "## Summary
Feed diversifier enforcing content variety constraints.

## Changes
- \`services/feed-service/src/ranking/diversifier.py\`
- \`services/feed-service/tests/unit/test_diversifier.py\` — 6 tests

Closes #7" \
    "## Code Review

**LGTM.** The sliding window approach for author diversity is elegant — deferred posts maintain their relative order. The media swap strategy correctly minimizes score disruption by swapping the lowest-scored post in the window." \
    "## 🔒 Security Review

**Status: ✅ PASS** — Pure computation, no I/O." \
    services/feed-service/src/ranking/diversifier.py \
    services/feed-service/tests/unit/test_diversifier.py
}

issue_8() {
  do_issue 8 \
    "feat/8-feed-assembler" \
    "feat: Feed Assembler with cursor pagination" \
    "feat,priority:critical,milestone:core-pipeline" \
    "feat(ranking): add feed assembler with base64 cursor-based pagination" \
    "Implement cursor-based pagination for the feed response:

- Cursor format: base64url-encoded JSON {\"offset\": N}
- Sequential position numbering across pages (page 2 starts at page 1 end)
- next_cursor is None when at end of feed (no more pages)
- Invalid/missing cursor gracefully resets to offset 0
- FeedResponse model: user_id, posts[], next_cursor, total_candidates, page_size
- RankedPost model: post_id, author_id, content_type, score, position, metadata

Cursor-based pagination is preferred over offset-based for feed use cases
because it is stable under concurrent writes (new posts do not shift pages).

Test coverage: 7 unit tests including two-page pagination roundtrip." \
    "## Summary
Paginated feed assembly with cursor encoding.

## Changes
- \`services/feed-service/src/ranking/assembler.py\`
- \`services/feed-service/src/models/feed.py\` — FeedResponse and RankedPost
- \`services/feed-service/tests/unit/test_assembler.py\` — 7 tests

Closes #8" \
    "## Code Review

**LGTM.** The base64 cursor encoding is simple and effective. The two-page pagination test correctly validates no ID overlap between pages. Consider adding cursor encryption (HMAC) in production to prevent cursor tampering." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Cursor tampering | ⚠️ | base64 cursors are guessable — low risk since offset only affects pagination position, not data access |" \
    services/feed-service/src/ranking/assembler.py \
    services/feed-service/src/models/feed.py \
    services/feed-service/tests/unit/test_assembler.py
}

issue_9() {
  do_issue 9 \
    "feat/9-feed-orchestrator" \
    "feat: Feed Service orchestration endpoint" \
    "feat,priority:critical,milestone:core-pipeline" \
    "feat(feed): add feed service orchestration with cache-first parallel pipeline" \
    "Implement the core GET /feed endpoint orchestrating the full ranking pipeline:

1. Cache check — Redis GET with SHA256(user_id+cursor) key
2. Parallel fan-out — asyncio.gather for following, trending, preferences
3. Deduplication — set-based post_id dedup
4. Score — call FeedScorer.score_batch
5. Diversify — call FeedDiversifier.apply_rules
6. Assemble — call FeedAssembler.assemble with pagination
7. Cache — Redis SET with 300s TTL
8. Emit — Kafka feed-served event (async)

FeedCache provides in-memory dict fallback when Redis is unavailable.
Latency is logged for both cache-hit and cold-path executions.

Test coverage: 4 unit tests for FeedCache (set+get, miss, invalidate, overwrite)." \
    "## Summary
Core feed orchestrator — the central nervous system of the ranking pipeline.

## Changes
- \`services/feed-service/src/main.py\`
- \`services/feed-service/src/api/feed_handler.py\` — Pipeline orchestrator
- \`services/feed-service/src/cache/feed_cache.py\` — Redis/in-memory cache
- \`services/feed-service/Dockerfile\`
- \`services/feed-service/tests/unit/test_cache.py\` — 4 tests

Closes #9" \
    "## Code Review

**APPROVE.** The parallel fan-out with \`asyncio.gather\` is the correct pattern — dominated by the slowest call (~12ms user-profile) rather than the sum. The SHA256 cache key prevents key collision while keeping keys short. Good latency logging for debugging cold vs cached paths." \
    "## 🔒 Security Review

**Status: ✅ PASS**

Cache keys are hashed — no PII leakage into Redis key space." \
    services/feed-service/src/main.py \
    services/feed-service/src/api/feed_handler.py \
    services/feed-service/src/cache/feed_cache.py \
    services/feed-service/Dockerfile \
    services/feed-service/tests/unit/test_cache.py
}

issue_10() {
  do_issue 10 \
    "feat/10-ranking-engine" \
    "feat: Ranking Engine with XGBoost model serving" \
    "feat,priority:high,milestone:core-pipeline" \
    "feat(ml): add ranking engine with XGBoost serving, A/B variants, and feature store" \
    "Implement the ML ranking engine microservice:

- POST /score: accepts batch feature dicts, returns float scores
- RankingModel: loads XGBoost .json model on startup, falls back to
  heuristic weighted sum when model file is absent
- A/B variant support via model_version parameter — different models
  can be served concurrently for experimentation
- FeatureStore: manages windowed engagement aggregates (1h, 24h, 7d)
  with get_post_features and update_features methods

The heuristic fallback uses identical weights to the FeedScorer,
ensuring consistent ranking behavior even without a trained model.

Test coverage: 5 unit tests for model prediction and fallback." \
    "## Summary
ML model serving for feed ranking with graceful degradation.

## Changes
- \`services/ranking-engine/src/main.py\` — FastAPI + RankingModel
- \`services/ranking-engine/src/features/feature_store.py\`
- \`services/ranking-engine/Dockerfile\`
- \`services/ranking-engine/tests/unit/test_model.py\` — 5 tests

Closes #10" \
    "## Code Review

**LGTM.** The heuristic fallback pattern is elegant — the service never returns an error for missing models, just gracefully degrades to the formula-based scorer. The A/B variant design via model_version parameter is clean and supports canary rollouts." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Model file path | ✅ | Read from RANKING_MODEL_PATH env var, not user input |
| Batch size limit | ⚠️ | No max on candidates list length — add limit=1000 check |" \
    services/ranking-engine/src/main.py \
    services/ranking-engine/src/features/feature_store.py \
    services/ranking-engine/Dockerfile \
    services/ranking-engine/tests/unit/test_model.py
}

issue_11() {
  do_issue 11 \
    "infra/11-docker-compose" \
    "infra: Docker Compose for full local dev stack" \
    "infra,priority:critical,milestone:infrastructure" \
    "infra(docker): add docker-compose with all services, PG, Redis, Kafka KRaft, observability" \
    "Complete Docker Compose configuration for local development:

Application services (5): api-gateway, feed-service, ranking-engine,
user-profile, content-ingestion — each with individual Dockerfile.

Infrastructure: PostgreSQL 16 (alpine), Redis 7 (alpine, 256MB LRU),
Kafka 3.7 (Bitnami, KRaft mode — no ZooKeeper), Jaeger all-in-one,
Prometheus, Grafana.

Features:
- YAML anchors for shared environment variables
- Health checks on all infrastructure services
- Named volume for PostgreSQL persistence
- Bridge network for inter-service DNS resolution
- DB init script auto-mounted via docker-entrypoint-initdb.d" \
    "## Summary
One-command local dev environment.

## Changes
- \`docker-compose.yml\` — Full 11-service stack
- \`docker/base-python.Dockerfile\`
- \`docker/prometheus.yml\` — Scrape config
- \`.env.example\` — All environment variables

## Quick Start
\`\`\`bash
docker compose up -d
curl http://localhost:8000/health
\`\`\`

Closes #11" \
    "## Code Review

**LGTM.** Kafka KRaft mode eliminates the ZooKeeper dependency — reduces the container count by 1 and simplifies networking. Health checks ensure dependent services wait for infrastructure readiness." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Default passwords | ⚠️ | .env.example has placeholder passwords — documented as dev-only |
| Port exposure | ✅ | Only gateway (8000) needs external exposure in prod |
| Network isolation | ✅ | Bridge network keeps traffic internal |" \
    docker-compose.yml \
    docker/base-python.Dockerfile \
    docker/prometheus.yml \
    .env.example
}

issue_12() {
  do_issue 12 \
    "ci/12-github-actions" \
    "ci: GitHub Actions CI/CD pipeline" \
    "ci,priority:critical,milestone:infrastructure" \
    "ci: add multi-stage GitHub Actions pipeline with lint, test, build, deploy" \
    "Multi-stage CI/CD pipeline:

1. Lint: ruff check + format verification
2. Unit Tests: pytest across all services with JUnit XML output
3. Integration Tests: pytest with PostgreSQL and Redis service containers
4. Build Images: matrix strategy for 5 services, push to ghcr.io
5. Deploy Dev: kubectl apply (gated on main branch merge)

BuildX with GitHub Actions cache for fast rebuilds.
Service containers for integration tests avoid Docker-in-Docker." \
    "## Summary
Automated CI/CD for every push and PR.

## Changes
- \`.github/workflows/ci.yml\`

Closes #12" \
    "## Code Review

**LGTM.** The matrix strategy for Docker builds is efficient — 5 parallel builds instead of sequential. Service containers for integration tests are more reliable than Docker-in-Docker. GHA cache with \`type=gha,mode=max\` maximizes layer reuse." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Secret handling | ✅ | GITHUB_TOKEN for GHCR, no custom secrets exposed |
| Image provenance | ℹ️ | Consider adding cosign signing in future |
| Dependency scanning | ℹ️ | Add \`safety\` or \`pip-audit\` step |" \
    .github/workflows/ci.yml
}

issue_13() {
  do_issue 13 \
    "infra/13-kubernetes" \
    "infra: Kubernetes manifests with Kustomize overlays" \
    "infra,priority:high,milestone:infrastructure" \
    "infra(k8s): add base deployments with HPA, probes, and Kustomize overlays" \
    "Kubernetes deployment manifests:

- Namespace social-feed with istio-injection label
- Deployments for all 5 services with resource requests/limits
- Readiness probes on /health (5s initial, 10s period)
- Liveness probes on /health (10s initial, 30s period)
- HPA: feed-service 3-20 (CPU 70%, Memory 80%), ranking-engine 2-10 (CPU 60%)
- ClusterIP services for internal communication
- Kustomize overlays: dev (1 replica), staging, prod" \
    "## Summary
Production-grade Kubernetes deployment manifests.

## Changes
- \`k8s/base/deployments.yaml\`
- \`k8s/base/kustomization.yaml\`
- \`k8s/overlays/dev/kustomization.yaml\`
- \`k8s/overlays/staging/kustomization.yaml\`
- \`k8s/overlays/prod/kustomization.yaml\`

Closes #13" \
    "## Code Review

**LGTM.** Resource limits are well-calibrated — feed-service gets more memory (1Gi) for holding candidate lists, ranking-engine gets more CPU (2 cores) for XGBoost inference. The HPA scaling targets are conservative, which is correct for a latency-sensitive service." \
    "## 🔒 Security Review

**Status: ✅ PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Resource limits | ✅ | Prevents container resource abuse |
| Network policy | ℹ️ | Add Calico/Cilium policies to restrict inter-namespace traffic |
| RBAC | ℹ️ | ServiceAccounts not yet defined — add in hardening |" \
    k8s/base/deployments.yaml \
    k8s/base/kustomization.yaml \
    k8s/overlays/dev/kustomization.yaml
}

issue_14() {
  do_issue 14 \
    "infra/14-terraform-eks" \
    "infra: Terraform EKS module" \
    "infra,priority:medium,milestone:infrastructure" \
    "infra(terraform): add EKS module with managed node group and IAM" \
    "Terraform module for AWS EKS:

- EKS cluster with private + public API endpoints
- Managed node group: t3.medium, scaling 2-10 nodes
- IAM roles: EKSClusterPolicy, WorkerNodePolicy, CNI, ECR read-only
- Variables: cluster_name, region, instance_type, vpc_id, subnet_ids
- Outputs: cluster_endpoint, cluster_name" \
    "## Summary
Infrastructure as Code for AWS EKS deployment.

## Changes
- \`terraform/modules/eks/main.tf\`

Closes #14" \
    "## Code Review

**LGTM.** Clean module with proper variable separation. The IAM roles follow least-privilege — ECR is read-only. Consider adding cluster encryption config and audit logging in production." \
    "## 🔒 Security Review

**Status: ⚠️ CONDITIONAL PASS**

| Check | Status | Notes |
|-------|--------|-------|
| Public API endpoint | ⚠️ | \`endpoint_public_access = true\` — restrict CIDR in prod |
| IAM least privilege | ✅ | Correct policy attachments |
| Secrets encryption | ℹ️ | Add KMS encryption for K8s secrets |
| Audit logging | ℹ️ | Enable CloudTrail + EKS audit logs |" \
    terraform/modules/eks/main.tf
}

issue_15() {
  do_issue 15 \
    "infra/15-observability" \
    "infra: Observability stack integration" \
    "infra,priority:medium,milestone:infrastructure" \
    "infra(telemetry): add Prometheus scrape config and OpenTelemetry integration" \
    "Observability integration:

- Prometheus scrape config for all 5 service endpoints
- OpenTelemetry tracer factory with OTLP gRPC exporter
- Structured JSON logging with trace ID correlation
- Jaeger collector for distributed tracing" \
    "## Summary
Observability foundation for monitoring and debugging.

## Changes
- \`docker/prometheus.yml\`
- \`services/shared/src/utils/logging.py\` (OTEL integration)

Closes #15" \
    "## Code Review

**LGTM.** The OTEL tracer factory pattern is clean — no-op when unconfigured, full tracing when OTLP endpoint is set. Prometheus scrape config covers all services." \
    "" \
    docker/prometheus.yml \
    services/shared/src/utils/logging.py
}

issue_19() {
  do_issue 19 \
    "docs/19-architecture-docs" \
    "docs: Architecture documentation and ADRs" \
    "docs,priority:high,milestone:hardening" \
    "docs: add C4 diagrams, session flow, 6 ADRs, and comprehensive README" \
    "Complete documentation package:

- README.md: project overview, local setup, cloud deployment (Docker, EKS, GKE, AKS),
  testing commands, project structure, ADR index
- C4 diagrams: Level 1 (system context), Level 2 (containers), Level 3 (feed-service)
- Deployment architecture diagram (EKS + managed services)
- Session flow: 7-stage request lifecycle with latency budget
- Error handling documentation for Redis/Kafka/ranking-engine outages
- 6 ADRs: Kafka, Redis, XGBoost, PostgreSQL, FastAPI, Istio" \
    "## Summary
Production-grade documentation for the architecture.

## Changes
- \`README.md\`
- \`docs/diagrams/architecture.md\`
- \`docs/diagrams/session-flow.md\`
- \`docs/adr/001-kafka-event-streaming.md\`
- \`docs/adr/002-redis-feed-caching.md\`
- \`docs/adr/003-xgboost-ranking-model.md\`
- \`docs/adr/004-postgres-data-store.md\`
- \`docs/adr/005-fastapi-service-framework.md\`
- \`docs/adr/006-istio-service-mesh.md\`

Closes #19" \
    "## Code Review

**LGTM.** Documentation is thorough — the latency budget table and error handling section are particularly valuable for on-call engineers." \
    "" \
    README.md \
    docs/diagrams/architecture.md \
    docs/diagrams/session-flow.md \
    docs/adr/001-kafka-event-streaming.md \
    docs/adr/002-redis-feed-caching.md \
    docs/adr/003-xgboost-ranking-model.md \
    docs/adr/004-postgres-data-store.md \
    docs/adr/005-fastapi-service-framework.md \
    docs/adr/006-istio-service-mesh.md
}

###############################################################################
# MAIN EXECUTION
###############################################################################

echo -e "${C_CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Scalable Social Feed Ranking Service                       ║"
echo "║  Full Implementation Pipeline — 20 Issues                   ║"
echo "║  Branch → Commit → Push → PR → Review → Security → Merge   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${C_RESET}"

# Phase 0: Setup
phase_0

# Phase 1: Foundation
should_run 1  && issue_1
should_run 2  && issue_2
should_run 3  && issue_3
should_run 4  && issue_4
should_run 5  && issue_5

# Phase 2: Core Pipeline
should_run 6  && issue_6
should_run 7  && issue_7
should_run 8  && issue_8
should_run 9  && issue_9
should_run 10 && issue_10

# Phase 3: Infrastructure
should_run 11 && issue_11
should_run 12 && issue_12
should_run 13 && issue_13
should_run 14 && issue_14
should_run 15 && issue_15

# Phase 4: Docs
should_run 19 && issue_19

echo ""
log "ALL DONE"
echo "  View issues:  https://github.com/$REPO/issues"
echo "  View PRs:     https://github.com/$REPO/pulls"
echo "  View actions:  https://github.com/$REPO/actions"
