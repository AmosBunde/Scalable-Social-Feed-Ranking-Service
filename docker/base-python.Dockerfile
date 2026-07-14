# --- Builder: install pinned dependencies into an isolated venv ---
FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.6 \
    uvicorn[standard]==0.30.6 \
    pydantic==2.10.4 \
    pydantic-settings==2.7.1 \
    aiokafka==0.11.0 \
    redis[hiredis]==5.2.1 \
    httpx==0.27.2 \
    PyJWT==2.9.0 \
    python-json-logger==2.0.7 \
    numpy==1.26.4 \
    scikit-learn==1.5.2 \
    pytest==8.3.4 \
    pytest-asyncio==0.23.8

# --- Runtime: slim image, venv + shared code only, non-root ---
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY services/shared /app/services/shared

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
