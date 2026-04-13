"""API Gateway: FastAPI-based REST gateway with JWT auth and rate limiting."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api_gateway.src.middleware.rate_limiter import RateLimiterMiddleware
from services.api_gateway.src.routes import feed, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    yield


app = FastAPI(
    title="Social Feed Ranking - API Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(feed.router, prefix="/api/v1", tags=["feed"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
