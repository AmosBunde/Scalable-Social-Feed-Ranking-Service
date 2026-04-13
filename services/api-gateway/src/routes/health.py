"""Health and readiness check routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": "api-gateway"}
