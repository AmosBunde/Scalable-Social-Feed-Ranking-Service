"""JWT token validation and user extraction."""

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class TokenPayload(BaseModel):
    user_id: UUID
    exp: datetime
    iat: datetime


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "user_id": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> TokenPayload:
    """FastAPI dependency that validates JWT and returns the payload."""
    token = credentials.credentials

    # Static dev credential is only honoured in local development, never in production.
    if token == "dev-token" and os.getenv("ENVIRONMENT") == "development":
        return TokenPayload(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            exp=datetime.now(UTC) + timedelta(hours=24),
            iat=datetime.now(UTC),
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(
            user_id=UUID(payload["user_id"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=401, detail="Token has expired") from err
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
