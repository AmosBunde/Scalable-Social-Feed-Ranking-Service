FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared /app/services/shared

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.* \
    uvicorn[standard]==0.30.* \
    pydantic==2.* \
    pydantic-settings==2.* \
    aiokafka==0.11.* \
    redis[hiredis]==5.* \
    httpx==0.27.* \
    PyJWT==2.* \
    python-json-logger==2.* \
    numpy==1.* \
    scikit-learn==1.* \
    pytest==8.* \
    pytest-asyncio==0.23.*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
