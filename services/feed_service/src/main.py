"""Feed Service: core orchestrator for feed generation."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.feed_service.src.api.feed_handler import router as feed_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Feed Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(feed_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "feed-service"}
