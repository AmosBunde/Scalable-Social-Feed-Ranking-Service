FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/services/shared
COPY services/ranking_engine /app/services/ranking_engine

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.* \
    uvicorn[standard]==0.30.* \
    pydantic==2.* \
    numpy==1.* \
    xgboost==2.* \
    python-json-logger==2.*

EXPOSE 8002

CMD ["uvicorn", "services.ranking_engine.src.main:app", "--host", "0.0.0.0", "--port", "8002"]
