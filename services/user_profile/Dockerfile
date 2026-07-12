FROM python:3.12-slim

WORKDIR /app

COPY services/shared /app/services/shared
COPY services/user_profile /app/services/user_profile

RUN pip install --no-cache-dir \
    fastapi[standard]==0.115.* \
    uvicorn[standard]==0.30.* \
    pydantic==2.* \
    pydantic-settings==2.* \
    httpx==0.27.* \
    python-json-logger==2.*

EXPOSE 8003

CMD ["uvicorn", "services.user_profile.src.main:app", "--host", "0.0.0.0", "--port", "8003"]
