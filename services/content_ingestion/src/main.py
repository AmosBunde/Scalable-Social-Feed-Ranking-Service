"""Content Ingestion Service: Kafka-based content and engagement pipeline."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Content ingestion service starting")
    yield
    logger.info("Content ingestion service shutting down")


app = FastAPI(title="Content Ingestion", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "content-ingestion"}
