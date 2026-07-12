"""Feed API routes."""

from fastapi import APIRouter, Depends, Query

from services.api_gateway.src.auth.jwt_handler import TokenPayload, verify_token

router = APIRouter()


@router.get("/feed")
async def get_feed(
    cursor: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    token: TokenPayload = Depends(verify_token),
):
    """Fetch a personalised ranked feed for the authenticated user.

    The feed owner is derived solely from the verified token so one user
    cannot request another user's feed.
    """
    effective_user_id = token.user_id
    # In production this forwards to feed-service via gRPC/HTTP
    return {
        "user_id": str(effective_user_id),
        "cursor": cursor,
        "limit": limit,
        "posts": [],
        "next_cursor": None,
    }
