# ADR 005: FastAPI as Service Framework

## Status
Accepted

## Context
Each microservice needs an HTTP framework supporting async I/O, automatic OpenAPI docs, request validation, dependency injection, and low overhead.

## Decision
Use FastAPI with Pydantic v2 for all Python services. Uvicorn as the ASGI server. Async handlers for all I/O-bound operations.

## Consequences
- **Positive**: Native async support, automatic OpenAPI/Swagger docs, Pydantic v2 validation is fast, dependency injection simplifies testing, strong typing with mypy.
- **Negative**: Python GIL limits CPU-bound concurrency per process. Single-threaded model requires multiple workers for CPU-heavy scoring.
- **Mitigated**: Uvicorn workers scale horizontally. XGBoost scoring is a C++ binding (releases GIL). Kubernetes HPA handles scaling.
