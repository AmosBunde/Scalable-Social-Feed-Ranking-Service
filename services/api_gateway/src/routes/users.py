"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.api_gateway.src.auth.jwt_handler import TokenPayload, verify_token

router = APIRouter()


@router.get("/users/{user_id}")
async def get_user(user_id: UUID, token: TokenPayload = Depends(verify_token)):
    # Profiles are public to any authenticated user (social-network semantics).
    return {"user_id": str(user_id), "profile": {}}


@router.post("/users/{user_id}/engagement")
async def post_engagement(
    user_id: UUID,
    token: TokenPayload = Depends(verify_token),
):
    if user_id != token.user_id:
        raise HTTPException(
            status_code=403, detail="Cannot record engagement for another user"
        )
    return {"status": "accepted"}
