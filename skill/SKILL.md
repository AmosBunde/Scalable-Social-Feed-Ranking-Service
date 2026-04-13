---
name: sfr-implementation
description: Skill for implementing the Scalable Social Feed Ranking Service. Covers microservice architecture with FastAPI, Kafka event streaming, Redis caching, XGBoost ranking, PostgreSQL persistence, Docker/K8s deployment, and CI/CD. Use this skill whenever working on feed ranking, engagement pipelines, ML scoring services, content diversification, or social graph queries in the SFR project. Also use when creating new services, adding tests, deploying infrastructure, or debugging any SFR component.
---

# Scalable Social Feed Ranking Service - Implementation Skill

## Architecture Overview

The system follows a microservices architecture with 5 core services, shared libraries, and infrastructure orchestration. Each service is independently deployable via Docker and Kubernetes.

### Service Map

| Service | Port | Framework | Responsibility |
|---------|------|-----------|----------------|
| api-gateway | 8000 | FastAPI | JWT auth, rate limiting, routing |
| feed-service | 8001 | FastAPI | Feed orchestration, assembly, pagination |
| ranking-engine | 8002 | FastAPI | XGBoost ML scoring, feature engineering |
| user-profile | 8003 | FastAPI | Social graph, user preferences |
| content-ingestion | 8004 | FastAPI | Kafka consumer/producer, engagement aggregation |

### Data Flow

```
Client -> API Gateway (JWT + rate limit)
  -> Feed Service (orchestrator)
    -> [parallel] User Profile (graph + prefs)
    -> [parallel] Content Ingestion (candidates)
    -> [parallel] Redis (cache check)
    -> Ranking Engine (XGBoost score)
    -> Diversifier (business rules)
    -> Assembler (pagination)
    -> Redis (cache set)
    -> Kafka (feed-served event)
  <- Response
```

## Implementation Standards

### Python Code Standards
- Python 3.12+, type hints mandatory
- Pydantic v2 for all data models
- async/await for all I/O operations
- Ruff for linting, Black formatting, mypy strict
- 80%+ test coverage per service

### File Naming Conventions
- Services: `services/<service-name>/src/<module>/<file>.py`
- Tests mirror source: `services/<service-name>/tests/unit/test_<file>.py`
- Shared code: `services/shared/src/<module>/<file>.py`

### Testing Patterns
- Unit tests: mock all external dependencies, test business logic
- Integration tests: use docker-compose.test.yml with real PG/Redis/Kafka
- E2E tests: full pipeline against dev environment
- Use `pytest-asyncio` for async test functions
- Fixtures in conftest.py per test directory

### Docker Build Pattern
Each service Dockerfile:
1. FROM python:3.12-slim
2. COPY shared libraries
3. COPY service source
4. pip install dependencies
5. CMD uvicorn with correct module path

### Kubernetes Deployment Pattern
- Base manifests in k8s/base/
- Environment overlays in k8s/overlays/{dev,staging,prod}/
- HPA on CPU (70%) and memory (80%) for feed-service and ranking-engine
- Readiness/liveness probes on /health endpoints

## Issue-by-Issue Implementation Guide

### Phase 1: Foundation (Issues #1-#5)

**Issue #1: Project scaffolding and shared libraries**
```
Files: services/shared/src/models/base.py, events/kafka_client.py, cache/redis_client.py, utils/logging.py
Tests: services/shared/tests/test_circuit_breaker.py
```

**Issue #2: PostgreSQL schema and migrations**
```
Files: scripts/init-db.sql, scripts/seed_data.py
Run: docker compose up postgres -d && psql < scripts/init-db.sql
```

**Issue #3: API Gateway with JWT and rate limiting**
```
Files: services/api-gateway/src/main.py, auth/jwt_handler.py, middleware/rate_limiter.py, routes/
Tests: tests/unit/test_jwt.py, test_rate_limiter.py, tests/integration/test_gateway_endpoints.py
```

**Issue #4: User Profile service with social graph**
```
Files: services/user-profile/src/main.py
Tests: services/user-profile/tests/unit/
```

**Issue #5: Content Ingestion with Kafka consumers**
```
Files: services/content-ingestion/src/main.py, consumers/engagement_consumer.py
Tests: tests/unit/test_engagement_consumer.py
```

### Phase 2: Core Pipeline (Issues #6-#10)

**Issue #6: Feed Scorer with weighted feature extraction**
```
Files: services/feed-service/src/ranking/scorer.py
Tests: tests/unit/test_scorer.py
Key: 6 feature groups, exponential recency decay (half-life 6h)
```

**Issue #7: Feed Diversifier with business rules**
```
Files: services/feed-service/src/ranking/diversifier.py
Tests: tests/unit/test_diversifier.py
Key: author cap per window, media mix, trending interleave
```

**Issue #8: Feed Assembler with cursor pagination**
```
Files: services/feed-service/src/ranking/assembler.py
Tests: tests/unit/test_assembler.py
Key: base64 cursor encoding, position tracking
```

**Issue #9: Feed Service orchestration endpoint**
```
Files: services/feed-service/src/api/feed_handler.py, cache/feed_cache.py
Tests: tests/unit/test_cache.py
Key: parallel fan-out, cache-first, emit events
```

**Issue #10: Ranking Engine with XGBoost serving**
```
Files: services/ranking-engine/src/main.py, features/feature_store.py
Tests: tests/unit/test_model.py
Key: heuristic fallback, A/B model variants
```

### Phase 3: Infrastructure (Issues #11-#15)

**Issue #11: Docker Compose for local dev**
```
Files: docker-compose.yml, docker/base-python.Dockerfile, .env.example
All service Dockerfiles
```

**Issue #12: GitHub Actions CI/CD pipeline**
```
Files: .github/workflows/ci.yml
Stages: lint -> unit test -> integration test -> build images -> deploy
```

**Issue #13: Kubernetes base manifests + Kustomize overlays**
```
Files: k8s/base/deployments.yaml, k8s/base/kustomization.yaml
k8s/overlays/{dev,staging,prod}/kustomization.yaml
```

**Issue #14: Terraform EKS module**
```
Files: terraform/modules/eks/main.tf
```

**Issue #15: Observability (Prometheus, Grafana, Jaeger)**
```
Files: docker/prometheus.yml, OpenTelemetry integration in shared/utils/logging.py
```

### Phase 4: Hardening (Issues #16-#20)

**Issue #16: Integration tests with docker-compose.test.yml**
**Issue #17: Load testing with k6**
**Issue #18: Istio service mesh configuration**
**Issue #19: Documentation: ADRs and architecture diagrams**
**Issue #20: Proto definitions for gRPC migration path**

## Common Commands

```bash
# Local dev
make dev                    # Start everything
make test                   # Run all tests
make test-service SVC=feed-service  # Test one service
make lint                   # Lint all code

# Docker
docker compose up -d        # Start stack
docker compose logs -f feed-service

# Kubernetes
kubectl apply -k k8s/overlays/dev/
kubectl get pods -n social-feed
kubectl logs -f deploy/feed-service -n social-feed

# Terraform
cd terraform/environments/prod
terraform init && terraform plan
```
