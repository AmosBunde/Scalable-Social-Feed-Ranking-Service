"""Unit tests for JWT authentication handler."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi.security import HTTPAuthorizationCredentials

from services.api_gateway.src.auth.jwt_handler import (
    create_access_token,
    verify_token,
    TokenPayload,
)


class TestJWTHandler:
    def test_create_and_verify_token(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = verify_token(creds)
        assert payload.user_id == user_id
        assert payload.exp > datetime.now(timezone.utc)

    def test_dev_token_works(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dev-token")
        payload = verify_token(creds)
        assert payload.user_id is not None

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
        with pytest.raises(HTTPException) as exc:
            verify_token(creds)
        assert exc.value.status_code == 401
