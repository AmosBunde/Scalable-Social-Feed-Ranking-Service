FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/services/shared
COPY services/content_ingestion /app/services/content_ingestion

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.* \
    uvicorn[standard]==0.30.* \
    pydantic==2.* \
    pydantic-settings==2.* \
    aiokafka==0.11.* \
    redis[hiredis]==5.* \
    httpx==0.27.* \
    python-json-logger==2.*

EXPOSE 8004

CMD ["uvicorn", "services.content_ingestion.src.main:app", "--host", "0.0.0.0", "--port", "8004"]
