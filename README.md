# Scalable Social Feed Ranking Service

> A distributed backend service that generates and ranks personalized content feeds for users based on engagement signals -- built for LinkedIn-scale throughput.

[![CI/CD](https://github.com/your-org/social-feed-ranking/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/social-feed-ranking/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Java 21](https://img.shields.io/badge/java-21-orange.svg)](https://openjdk.org/)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Service Descriptions](#service-descriptions)
- [Feed Ranking Pipeline](#feed-ranking-pipeline)
- [Configuration](#configuration)
- [Testing Strategy](#testing-strategy)
- [Deployment](#deployment)
  - [Docker Compose (Local)](#docker-compose-local)
  - [AWS (EKS)](#aws-eks)
  - [GCP (GKE)](#gcp-gke)
  - [Azure (AKS)](#azure-aks)
  - [Terraform](#terraform)
  - [Kubernetes](#kubernetes)
  - [Istio Service Mesh](#istio-service-mesh)
  - [Kiali Observability](#kiali-observability)
- [Architecture Decision Records](#architecture-decision-records)
- [Contributing](#contributing)

---

## Architecture Overview

The system simulates the backend of a social platform's feed. When a user opens the app, the Feed Service retrieves candidate posts from multiple sources, scores them with a ranking model using engagement signals (likes, comments, follows, dwell time), assembles a personalized feed, and caches the result. Events stream to Kafka for analytics and model retraining.

```
User Request (GET /feed)
        |
        v
  [API Gateway] ── REST + JWT ──> Clients
        |
        v
  [Feed Service]
        |
        ├──> [User Profile Service]     ── fetch preferences + social graph
        |
        ├──> [Content Ingestion]        ── candidate post retrieval
        |         |
        |    [Kafka Streams]            ── real-time engagement events
        |
        ├──> [Ranking Engine]           ── ML scoring pipeline
        |         |
        |    [Feature Store]            ── engagement features
        |
        ├──> [Redis Cache]              ── ranked feed caching (L1)
        |
        └──> [PostgreSQL]               ── user/content persistent store
                  |
                  v
         [Kafka] ── analytics events + model retraining signals
```

### Feed Generation Pipeline

1. **Retrieve** -- Fetch candidate posts from followed users, trending content, and algorithmic suggestions
2. **Enrich** -- Attach engagement features (like count, comment count, share velocity, author reputation)
3. **Score** -- Ranking model assigns a relevance score per post per user
4. **Diversify** -- Apply diversity rules (no duplicate authors in top 5, mix content types)
5. **Assemble** -- Construct the final ordered feed with pagination cursors
6. **Cache** -- Store the ranked feed in Redis with TTL for low-latency repeat access
7. **Emit** -- Publish feed-served events to Kafka for analytics and model feedback

---

## Tech Stack

| Component              | Technology                           | Purpose                                   |
|------------------------|--------------------------------------|-------------------------------------------|
| **Feed Service**       | Python 3.12 (FastAPI)                | Feed assembly, ranking orchestration      |
| **Content Ingestion**  | Java 21 (Spring Boot) / Python       | Post ingestion, Kafka consumer/producer   |
| **Ranking Engine**     | Python 3.12 (scikit-learn / XGBoost) | ML-based feed scoring                     |
| **User Profile**       | Python 3.12 (FastAPI)                | User preferences, social graph queries    |
| **API Gateway**        | Python 3.12 (FastAPI)                | Auth, rate limiting, request routing      |
| **Event Streaming**    | Apache Kafka 3.7                     | Engagement events, analytics pipeline     |
| **Feed Cache**         | Redis 7.x (Cluster)                  | Ranked feed caching, feature store cache  |
| **Data Store**         | PostgreSQL 16                        | Users, posts, engagement history          |
| **Container Orchestration** | Kubernetes (EKS/GKE/AKS)       | Production deployment                     |
| **Service Mesh**       | Istio + Kiali                        | Traffic management, observability         |
| **IaC**                | Terraform 1.7+                       | Multi-cloud infrastructure                |
| **CI/CD**              | GitHub Actions                       | Build, test, deploy pipelines             |
| **Monitoring**         | Prometheus + Grafana                 | Metrics and dashboards                    |
| **Tracing**            | OpenTelemetry + Jaeger               | Distributed tracing                       |

---

## Project Structure

```
social-feed-ranking/
├── README.md
├── docker-compose.yml
├── docker-compose.test.yml
├── Makefile
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── proto/
│   ├── feed.proto
│   └── engagement.proto
├── services/
│   ├── api-gateway/                    # REST gateway (FastAPI)
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── feed.py
│   │   │   │   ├── users.py
│   │   │   │   └── health.py
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   └── jwt_handler.py
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── rate_limiter.py
│   │   │   │   └── logging.py
│   │   │   ├── config/
│   │   │   │   └── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── feed-service/                   # Feed assembly + ranking orchestration
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── feed_handler.py
│   │   │   ├── ranking/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scorer.py
│   │   │   │   ├── diversifier.py
│   │   │   │   └── assembler.py
│   │   │   ├── cache/
│   │   │   │   ├── __init__.py
│   │   │   │   └── feed_cache.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── feed.py
│   │   │   │   └── post.py
│   │   │   ├── config/
│   │   │   │   └── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── content-ingestion/              # Kafka-based content pipeline
│   │   ├── src/
│   │   │   ├── consumers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engagement_consumer.py
│   │   │   │   └── post_consumer.py
│   │   │   ├── producers/
│   │   │   │   ├── __init__.py
│   │   │   │   └── event_producer.py
│   │   │   ├── processors/
│   │   │   │   ├── __init__.py
│   │   │   │   └── engagement_aggregator.py
│   │   │   ├── models/
│   │   │   │   └── events.py
│   │   │   ├── config/
│   │   │   │   └── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── ranking-engine/                 # ML ranking model
│   │   ├── src/
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── xgboost_ranker.py
│   │   │   ├── features/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── feature_store.py
│   │   │   │   └── feature_engineering.py
│   │   │   ├── training/
│   │   │   │   ├── __init__.py
│   │   │   │   └── trainer.py
│   │   │   ├── serving/
│   │   │   │   ├── __init__.py
│   │   │   │   └── model_server.py
│   │   │   ├── config/
│   │   │   │   └── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── user-profile/                   # User data + social graph
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── profile_handler.py
│   │   │   ├── repository/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_repo.py
│   │   │   │   └── graph_repo.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── user.py
│   │   │   ├── config/
│   │   │   │   └── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── shared/                         # Shared libraries
│       ├── src/
│       │   ├── events/
│       │   │   └── kafka_client.py
│       │   ├── models/
│       │   │   ├── base.py
│       │   │   └── enums.py
│       │   ├── cache/
│       │   │   └── redis_client.py
│       │   └── utils/
│       │       ├── logging.py
│       │       └── telemetry.py
│       └── tests/
├── terraform/
│   ├── modules/
│   │   ├── vpc/
│   │   ├── eks/
│   │   ├── gke/
│   │   ├── aks/
│   │   ├── redis/
│   │   ├── postgres/
│   │   ├── kafka/
│   │   └── docker-registry/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── k8s/
│   ├── base/
│   ├── overlays/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   ├── service-mesh/
│   └── kiali/
├── docker/
│   ├── feed-service.Dockerfile
│   └── base-python.Dockerfile
├── docs/
│   ├── adr/
│   │   ├── 001-kafka-event-streaming.md
│   │   ├── 002-redis-feed-caching.md
│   │   ├── 003-xgboost-ranking-model.md
│   │   ├── 004-postgres-data-store.md
│   │   ├── 005-fastapi-service-framework.md
│   │   └── 006-istio-service-mesh.md
│   └── diagrams/
│       └── session-flow.md
└── scripts/
    ├── generate-structure.sh
    ├── setup-dev.sh
    ├── seed-data.sh
    └── run-tests.sh
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Java 21 (for Content Ingestion service, optional)
- Docker 24+ and Docker Compose v2
- Terraform 1.7+ (for cloud deployments)
- kubectl 1.29+ (for Kubernetes)
- istioctl 1.21+ (for service mesh)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/social-feed-ranking.git
cd social-feed-ranking

# Run the setup script
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker compose up -d

# Seed sample data
./scripts/seed-data.sh

# Verify health
curl http://localhost:8000/health

# Fetch a sample feed
curl -H "Authorization: Bearer dev-token" http://localhost:8000/api/v1/feed?user_id=user_001
```

### Quick Start with Make

```bash
make setup              # Install all dependencies
make dev                # Start development environment
make seed               # Load sample users, posts, engagement data
make test               # Run all tests
make test-unit          # Run unit tests only
make test-integration   # Run integration tests (requires Docker)
make lint               # Run linters
make build              # Build all Docker images
make deploy-dev         # Deploy to dev cluster
```

---

## Service Descriptions

### API Gateway (`services/api-gateway`)
FastAPI-based REST gateway. Handles JWT authentication, per-user rate limiting (token bucket), CORS, request validation, and routes to internal services. Exposes `/api/v1/feed`, `/api/v1/users`, and `/api/v1/engagement` endpoints.

### Feed Service (`services/feed-service`)
The core orchestrator. On each feed request it retrieves candidate posts from the Content Ingestion layer, fetches user preferences from the User Profile service, calls the Ranking Engine for scoring, applies diversity rules, assembles the paginated feed, caches it in Redis, and emits feed-served events to Kafka.

### Content Ingestion (`services/content-ingestion`)
Kafka consumer and producer pipeline. Consumes raw post-creation events and engagement events (likes, comments, shares, follows) from upstream producers. Aggregates engagement signals into windowed counters (1h, 24h, 7d) and writes enriched content records to PostgreSQL. Produces feed-invalidation events when engagement spikes above thresholds.

### Ranking Engine (`services/ranking-engine`)
ML-powered scoring service. Serves a pre-trained XGBoost model via a lightweight FastAPI endpoint. Features include author-user affinity, post recency decay, engagement velocity (likes/hour), content-type preference, and social proof signals. Supports A/B model variants for experimentation. Training pipeline reads from Kafka and the feature store.

### User Profile (`services/user-profile`)
Manages user data and the social graph. Provides user preferences (content-type weights, muted authors), follow/follower relationships, and interaction history. The social graph powers the "posts from people you follow" candidate retrieval path.

### Shared Libraries (`services/shared`)
Common code: Kafka producer/consumer wrappers, Redis client with circuit breaker, Pydantic base models, structured logging, and OpenTelemetry instrumentation.

---

## Feed Ranking Pipeline

### Candidate Retrieval (Fan-Out on Read)

```
User opens feed
      |
      v
  ┌─────────────────────────────────────┐
  │         Candidate Sources            │
  │                                      │
  │  [Following]  [Trending]  [Explore]  │
  │   ~200 posts   ~50 posts   ~50 posts │
  └─────────────────────────────────────┘
      |
      v
  ~300 candidate posts (deduplicated)
```

### Scoring

Each candidate post receives a score based on:

```
score = w1 * author_affinity       (0-1, based on past interactions)
      + w2 * engagement_velocity   (normalized likes/hour in first 4h)
      + w3 * recency_decay         (exponential decay, half-life = 6h)
      + w4 * content_type_pref     (user's preference for images/text/video)
      + w5 * social_proof          (# of mutual connections who engaged)
      + w6 * post_quality          (length, media, hashtag relevance)
```

The XGBoost model learns optimal weights from historical click-through and dwell-time data.

### Diversity Rules

After scoring, the diversifier enforces:
- No more than 2 posts from the same author in any window of 10
- At least 1 image/video post in every window of 5
- Trending posts interleaved at positions 3, 8, 15
- Sponsored content capped at 1 per 10 organic posts

---

## Configuration

All services use hierarchical configuration:

1. **Defaults** -- Hardcoded in `config/settings.py`
2. **Environment files** -- `.env` for local development
3. **Environment variables** -- Override via `SFR_<SERVICE>_<KEY>`
4. **Kubernetes ConfigMaps/Secrets** -- Production

### Key Environment Variables

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=feed-service-group
KAFKA_ENGAGEMENT_TOPIC=engagement-events
KAFKA_FEED_TOPIC=feed-events
KAFKA_POST_TOPIC=post-events

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=social_feed
POSTGRES_USER=feed_user
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>
REDIS_FEED_TTL_SECONDS=300
REDIS_FEATURE_TTL_SECONDS=3600

# Ranking Engine
RANKING_MODEL_PATH=/models/xgboost_v1.json
RANKING_MODEL_VERSION=v1
RANKING_CANDIDATE_LIMIT=300
RANKING_RESULT_SIZE=50

# Service Ports
GATEWAY_PORT=8000
FEED_SERVICE_PORT=8001
RANKING_ENGINE_PORT=8002
USER_PROFILE_PORT=8003
CONTENT_INGESTION_PORT=8004

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Testing Strategy

### Test Pyramid

```
       /  E2E Tests  \          -- Full feed generation flow
      / Integration    \        -- Service + Kafka + Redis + PG
     / Unit Tests        \      -- Business logic isolation
    /____________________\
```

### Running Tests

```bash
# All tests
make test

# By layer
make test-unit           # Mocked dependencies, fast
make test-integration    # Requires docker-compose.test.yml
make test-e2e            # Full pipeline against dev environment

# By service
make test-service SVC=feed-service
make test-service SVC=ranking-engine

# With coverage
make test-coverage       # HTML report in htmlcov/

# Load testing (requires k6)
make test-load           # Simulate 1000 concurrent feed requests
```

### Test Environment (`docker-compose.test.yml`)

Spins up isolated PostgreSQL, Redis, and Kafka (KRaft mode, no ZooKeeper) with pre-seeded data for deterministic integration tests. The ranking engine loads a frozen test model for reproducible scores.

---

## Deployment

### Docker Compose (Local)

```bash
docker compose up -d
docker compose logs -f feed-service
```

### Terraform Multi-Cloud

```bash
cd terraform/environments/prod

terraform init
terraform plan -var="cloud_provider=aws"
terraform apply -var="cloud_provider=aws" -auto-approve
```

#### AWS (EKS)

```bash
aws configure
cd terraform/environments/prod
terraform apply -var="cloud_provider=aws"
aws eks update-kubeconfig --name sfr-cluster --region us-east-1
kubectl apply -k k8s/overlays/prod/
```

#### GCP (GKE)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
cd terraform/environments/prod
terraform apply -var="cloud_provider=gcp"
gcloud container clusters get-credentials sfr-cluster --zone us-central1-a
kubectl apply -k k8s/overlays/prod/
```

#### Azure (AKS)

```bash
az login
cd terraform/environments/prod
terraform apply -var="cloud_provider=azure"
az aks get-credentials --resource-group sfr-rg --name sfr-cluster
kubectl apply -k k8s/overlays/prod/
```

### Kubernetes

```bash
kubectl apply -k k8s/overlays/dev/       # Dev
kubectl apply -k k8s/overlays/staging/   # Staging
kubectl apply -k k8s/overlays/prod/      # Production

kubectl get pods -n social-feed
kubectl logs -f deployment/feed-service -n social-feed
kubectl scale deployment ranking-engine --replicas=5 -n social-feed
```

### Istio Service Mesh

```bash
istioctl install --set profile=production
kubectl label namespace social-feed istio-injection=enabled
kubectl apply -f k8s/service-mesh/
istioctl analyze -n social-feed
```

### Kiali Observability

```bash
kubectl apply -f k8s/kiali/
kubectl port-forward svc/kiali -n istio-system 20001:20001
# Open http://localhost:20001
```

---

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](docs/adr/001-kafka-event-streaming.md) | Kafka for Event Streaming | Accepted |
| [002](docs/adr/002-redis-feed-caching.md) | Redis for Feed Caching | Accepted |
| [003](docs/adr/003-xgboost-ranking-model.md) | XGBoost for Feed Ranking | Accepted |
| [004](docs/adr/004-postgres-data-store.md) | PostgreSQL for Persistent Storage | Accepted |
| [005](docs/adr/005-fastapi-service-framework.md) | FastAPI as Service Framework | Accepted |
| [006](docs/adr/006-istio-service-mesh.md) | Istio Service Mesh with Kiali | Accepted |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`make test`)
5. Commit (`git commit -m 'feat: add amazing feature'`)
6. Push and open a Pull Request

### Code Standards

- Python: Ruff linter, Black formatter, mypy strict
- Java: Checkstyle, SpotBugs
- All services: 80%+ test coverage, docstrings on public APIs
- Kafka schemas: Avro with Schema Registry versioning

---

## License

MIT License. See [LICENSE](LICENSE) for details.
