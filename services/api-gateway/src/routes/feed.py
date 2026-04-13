"""Feed API routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from services.api_gateway.src.auth.jwt_handler import TokenPayload, verify_token

router = APIRouter()


@router.get("/feed")
async def get_feed(
    user_id: Optional[UUID] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    token: TokenPayload = Depends(verify_token),
):
    """Fetch a personalised ranked feed for the authenticated user."""
    effective_user_id = user_id or token.user_id
    # In production this forwards to feed-service via gRPC/HTTP
    return {
        "user_id": str(effective_user_id),
        "cursor": cursor,
        "limit": limit,
        "posts": [],
        "next_cursor": None,
    }
