# --- Builder: install pinned dependencies into an isolated venv ---
FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.6 \
    uvicorn[standard]==0.30.6 \
    pydantic==2.10.4 \
    numpy==1.26.4 \
    xgboost==2.1.3 \
    python-json-logger==2.0.7

# --- Runtime: slim image, venv + app code only, non-root ---
FROM python:3.12-slim

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY services/shared /app/services/shared
COPY services/ranking_engine /app/services/ranking_engine

USER app

EXPOSE 8002

CMD ["uvicorn", "services.ranking_engine.src.main:app", "--host", "0.0.0.0", "--port", "8002"]
