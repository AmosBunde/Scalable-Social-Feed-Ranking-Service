"""User API routes."""
from uuid import UUID

from fastapi import APIRouter, Depends

from services.api_gateway.src.auth.jwt_handler import TokenPayload, verify_token

router = APIRouter()


@router.get("/users/{user_id}")
async def get_user(user_id: UUID, token: TokenPayload = Depends(verify_token)):
    return {"user_id": str(user_id), "profile": {}}


@router.post("/users/{user_id}/engagement")
async def post_engagement(
    user_id: UUID,
    token: TokenPayload = Depends(verify_token),
):
    return {"status": "accepted"}
