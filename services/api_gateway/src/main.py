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

# Wildcard origins with credentials is unsafe; default to local dev origins
# and require an explicit CORS_ORIGINS allowlist everywhere else.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip() and o.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimiterMiddleware)

app.include_router(health.router, tags=["health"])
app.include_router(feed.router, prefix="/api/v1", tags=["feed"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
