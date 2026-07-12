# Scalable Social Feed Ranking Service

A distributed backend service that generates and ranks personalised content feeds for users based on engagement signals, built for LinkedIn-scale throughput.

[![CI/CD](https://github.com/AmosBunde/Scalable-Social-Feed-Ranking-Service/actions/workflows/ci.yml/badge.svg)](https://github.com/AmosBunde/Scalable-Social-Feed-Ranking-Service/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

## Architecture

The system follows a microservices architecture with 5 core services communicating through REST (with a gRPC migration path), Kafka for event streaming, Redis for caching, and PostgreSQL for persistence. Each service is independently deployable and horizontally scalable.

**Services:**
- **API Gateway** (port 8000): JWT authentication, token bucket rate limiting, request routing
- **Feed Service** (port 8001): Core orchestrator for feed generation pipeline (retrieve, score, diversify, assemble, cache, emit)
- **Ranking Engine** (port 8002): XGBoost ML model serving with A/B variant support and heuristic fallback
- **User Profile** (port 8003): Social graph management, user preferences, follow/follower relationships
- **Content Ingestion** (port 8004): Kafka consumer/producer for engagement events, windowed aggregation, spike detection

**Infrastructure:**
- Apache Kafka 3.7 (KRaft mode) for event streaming
- Redis 7.x for ranked feed caching (300s TTL) and feature store
- PostgreSQL 16 for persistent storage with materialized views
- Prometheus + Grafana + Jaeger for observability
- Kubernetes with Istio service mesh for production deployment

See `docs/diagrams/architecture.md` for C4 diagrams and `docs/diagrams/session-flow.md` for the request lifecycle.

## Scalability

How the tree scales, and where the current limits are:

- **Stateless services**: all five services keep no request state in
  process (feeds cache in Redis, events flow through Kafka), so every
  service scales horizontally. HPA is pre-configured for the hot paths
  (feed-service 3-20 replicas, ranking-engine 2-10).
- **Independent deployment units**: one image per service
  (`services/<name>/Dockerfile`), built and pushed individually by CI —
  a change to the ranking model ships without touching the gateway.
- **Async ingestion**: engagement writes land in Kafka and are consumed
  out-of-band, so write spikes don't block feed reads. Partition counts
  are the scaling lever.
- **Read path protection**: Redis feed cache (300s TTL) absorbs repeat
  reads; the gateway rate-limits per caller; Istio adds retries,
  timeouts, circuit breaking, and a canary path for risky rollouts.
- **Known single points to watch**: PostgreSQL is a single primary
  (add read replicas / partitioning before write volume grows), the
  in-memory rate limiter is per-replica (move to Redis for a global
  limit), and Kafka runs single-broker outside production overlays.

## Quick Start (one command)

With Docker 24+ and Make installed:

```bash
make quickstart
```

This builds all five service images, starts the full stack (services +
Postgres/Redis/Kafka + Jaeger/Prometheus/Grafana), waits for every
container's health check, and verifies an authenticated feed request
end-to-end. When it finishes you have:

| Endpoint | URL |
|---|---|
| API gateway | http://localhost:8000 (auth: `Bearer dev-token`) |
| Jaeger traces | http://localhost:16686 |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |

If a default port is taken on your machine, override it:
`HOST_GATEWAY_PORT=18080 make quickstart` (same pattern:
`HOST_FEED_PORT`, `HOST_RANKING_PORT`, `HOST_PROFILE_PORT`,
`HOST_INGESTION_PORT`, `HOST_KAFKA_PORT`). Stop everything with
`make stop`; wipe volumes with `make clean`.

The `dev-token` bearer token only works because compose sets
`ENVIRONMENT=development` — production deployments use real signed JWTs.

## Local Development Setup

### Prerequisites

- Python 3.12+
- Docker 24+ and Docker Compose v2
- Make (optional but recommended)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/AmosBunde/Scalable-Social-Feed-Ranking-Service.git
cd Scalable-Social-Feed-Ranking-Service

# 2. Copy environment variables
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# 3. Start all services and infrastructure
docker compose up -d

# 4. Wait for health checks to pass (~30 seconds)
docker compose ps
# All services should show "healthy"

# 5. Seed sample data
python scripts/seed_data.py

# 6. Verify the API gateway
curl http://localhost:8000/health
# {"status":"healthy","service":"api-gateway"}

# 7. Fetch a sample feed (the feed owner is derived from the JWT)
curl -H "Authorization: Bearer dev-token" \
  "http://localhost:8000/api/v1/feed"

# 8. View Jaeger traces
open http://localhost:16686

# 9. View Grafana dashboards
open http://localhost:3000
# Login: admin / admin
```

### Running Without Docker

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Start infrastructure only
docker compose up postgres redis kafka -d

# 4. Run individual services
uvicorn services.api_gateway.src.main:app --port 8000 --reload
uvicorn services.feed_service.src.main:app --port 8001 --reload
uvicorn services.ranking_engine.src.main:app --port 8002 --reload
uvicorn services.user_profile.src.main:app --port 8003 --reload
```

### Running Tests

```bash
# All tests
make test

# Unit tests only (fast, no Docker needed)
make test-unit

# Integration tests (requires Docker infrastructure)
make test-integration

# Single service
make test-service SVC=feed-service

# With coverage report
make test-coverage
# Open htmlcov/index.html
```

## Cloud Deployment

### Option A: Docker Compose on a Single VM

For staging or small-scale production on a single cloud VM (AWS EC2, GCP Compute, Azure VM):

```bash
# SSH into your VM
ssh user@your-vm-ip

# Clone and configure
git clone https://github.com/AmosBunde/Scalable-Social-Feed-Ranking-Service.git
cd Scalable-Social-Feed-Ranking-Service
cp .env.example .env
# Edit .env with production values (strong passwords, real JWT secret)

# Build and start
docker compose -f docker-compose.yml up -d --build

# Verify
curl http://localhost:8000/health
```

### Container images

Every push to `main` builds and pushes one image per service to GHCR
(`.github/workflows/ci.yml`):

```
ghcr.io/amosbunde/sfr-api_gateway:{latest,<sha>}
ghcr.io/amosbunde/sfr-feed_service:{latest,<sha>}
ghcr.io/amosbunde/sfr-ranking_engine:{latest,<sha>}
ghcr.io/amosbunde/sfr-user_profile:{latest,<sha>}
ghcr.io/amosbunde/sfr-content_ingestion:{latest,<sha>}
```

The Kubernetes manifests in `k8s/base` reference exactly these names, so
`kubectl apply -k` works with no image edits. To deploy a specific
version, pin the `<sha>` tag in an overlay.

New GHCR packages are **private** by default: either make them public
(package settings on GitHub) or give the cluster an image pull secret:

```bash
kubectl create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io --docker-username=<user> \
  --docker-password=<PAT with read:packages> -n social-feed
# then add `imagePullSecrets: [{name: ghcr-pull}]` to the pod specs
```

Continuous deploy to a dev cluster is off by default (the job skips).
To enable it, set the repository variable `DEPLOY_TO_DEV=true` and add
a `KUBE_CONFIG` secret (base64-encoded kubeconfig); every main push
then applies `k8s/overlays/dev` after images publish.

### Option B: AWS EKS with Terraform

```bash
# 1. Configure AWS credentials
aws configure

# 2. Initialize Terraform
cd terraform/environments/prod
terraform init

# 3. Plan and apply
terraform plan -var="cloud_provider=aws"
terraform apply -var="cloud_provider=aws" -auto-approve

# 4. Configure kubectl
aws eks update-kubeconfig --name sfr-cluster --region us-east-1

# 5. Deploy application
kubectl apply -k k8s/overlays/prod/

# 6. Verify
kubectl get pods -n social-feed
kubectl logs -f deployment/feed-service -n social-feed

# 7. (Optional) add the Istio service mesh layer:
#    STRICT mTLS, per-service authorization, retries/timeouts,
#    and a canary rollout path for ranking-engine
kubectl apply -k k8s/istio/
# See k8s/istio/README.md for canary and Kiali instructions
```

### Option C: GCP GKE

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

cd terraform/environments/prod
terraform apply -var="cloud_provider=gcp"

gcloud container clusters get-credentials sfr-cluster --zone us-central1-a
kubectl apply -k k8s/overlays/prod/
```

### Option D: Azure AKS

```bash
az login

cd terraform/environments/prod
terraform apply -var="cloud_provider=azure"

az aks get-credentials --resource-group sfr-rg --name sfr-cluster
kubectl apply -k k8s/overlays/prod/
```

### Istio Service Mesh (Production)

```bash
istioctl install --set profile=production
kubectl label namespace social-feed istio-injection=enabled
kubectl apply -k k8s/istio/
istioctl analyze -n social-feed
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment feed-service --replicas=10 -n social-feed

# HPA is pre-configured:
# feed-service: 3-20 replicas (CPU 70%, Memory 80%)
# ranking-engine: 2-10 replicas (CPU 60%)
kubectl get hpa -n social-feed
```

## Feed Ranking Pipeline

The ranking pipeline processes ~300 candidate posts per request through 7 stages:

1. **Retrieve**: Fan-out to following (200), trending (50), and explore (50) sources
2. **Enrich**: Attach engagement features from the feature store (1h, 24h, 7d windows)
3. **Score**: XGBoost model scores each candidate using 6 feature groups (author affinity, engagement velocity, recency decay, content type preference, social proof, post quality)
4. **Diversify**: Enforce business rules (max 2 per author in 10, media mix, trending interleave)
5. **Assemble**: Construct paginated response with cursor-based pagination
6. **Cache**: Store in Redis with 300s TTL
7. **Emit**: Publish feed-served event to Kafka for analytics

Latency targets: p50 < 30ms (cold), p50 < 3ms (cached), p99 < 80ms (cold).

## Project Structure

```
social-feed-ranking/
├── services/                 # One importable package per service,
│   ├── api_gateway/          #   each with its own Dockerfile
│   ├── feed_service/         # Feed orchestration and ranking
│   ├── ranking_engine/       # XGBoost model serving
│   ├── user_profile/         # Social graph and preferences
│   ├── content_ingestion/    # Kafka event pipeline
│   └── shared/               # Common libraries
├── proto/                    # gRPC contracts (migration path)
├── tests/
│   ├── integration/          # Cross-service + container-backed tests
│   └── load/                 # k6 load scenarios with SLO thresholds
├── k8s/                      # Kubernetes manifests (Kustomize)
│   ├── base/ + overlays/     # dev/staging/prod variants with HPA
│   └── istio/                # Service mesh: mTLS, authz, canary
├── terraform/                # Infrastructure as Code (AWS/GCP/Azure)
├── docker/                   # Shared Docker configuration
├── docs/                     # Architecture docs, ADRs, diagrams
├── scripts/                  # Setup, seed, and utility scripts
├── .github/workflows/        # CI: lint, test, build+push images, deploy
├── docker-compose.yml        # Local development stack
├── docker-compose.test.yml   # Isolated infra for integration tests
├── Makefile                  # quickstart, test, deploy commands
└── requirements-dev.txt      # Python dependencies
```

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](docs/adr/001-kafka-event-streaming.md) | Kafka for Event Streaming | Accepted |
| [002](docs/adr/002-redis-feed-caching.md) | Redis for Feed Caching | Accepted |
| [003](docs/adr/003-xgboost-ranking-model.md) | XGBoost for Feed Ranking | Accepted |
| [004](docs/adr/004-postgres-data-store.md) | PostgreSQL for Persistent Storage | Accepted |
| [005](docs/adr/005-fastapi-service-framework.md) | FastAPI as Service Framework | Accepted |
| [006](docs/adr/006-istio-service-mesh.md) | Istio Service Mesh with Kiali | Accepted |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`make test`)
5. Lint your code (`make lint`)
6. Commit with conventional prefix (`git commit -m 'feat: add amazing feature'`)
7. Push and open a Pull Request

## License

MIT License. See [LICENSE](LICENSE) for details.
