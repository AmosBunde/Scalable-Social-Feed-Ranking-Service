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

# 7. Fetch a sample feed
curl -H "Authorization: Bearer dev-token" \
  "http://localhost:8000/api/v1/feed?user_id=00000000-0000-0000-0000-000000000001"

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
kubectl apply -f k8s/service-mesh/
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
├── services/
│   ├── api-gateway/          # REST gateway, JWT, rate limiting
│   ├── feed-service/         # Feed orchestration and ranking
│   ├── ranking-engine/       # XGBoost model serving
│   ├── user-profile/         # Social graph and preferences
│   ├── content-ingestion/    # Kafka event pipeline
│   └── shared/               # Common libraries
├── k8s/                      # Kubernetes manifests (Kustomize)
├── terraform/                # Infrastructure as Code (AWS/GCP/Azure)
├── docker/                   # Docker configurations
├── docs/                     # Architecture docs, ADRs, diagrams
├── scripts/                  # Setup, seed, and utility scripts
├── skill/                    # Claude implementation skill
├── .github/workflows/        # CI/CD pipeline
├── docker-compose.yml        # Local development stack
├── Makefile                  # Build and test commands
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
