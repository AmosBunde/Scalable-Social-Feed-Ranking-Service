"""Unit tests for JWT authentication handler."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from services.api_gateway.src.auth.jwt_handler import (
    create_access_token,
    verify_token,
)


class TestJWTHandler:
    def test_create_and_verify_token(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = verify_token(creds)
        assert payload.user_id == user_id
        assert payload.exp > datetime.now(UTC)

    def test_dev_token_works_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dev-token")
        payload = verify_token(creds)
        assert payload.user_id is not None

    def test_dev_token_rejected_outside_development(self, monkeypatch):
        from fastapi import HTTPException

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dev-token")
        with pytest.raises(HTTPException) as exc:
            verify_token(creds)
        assert exc.value.status_code == 401

    def test_invalid_token_raises(self):
        from fastapi import HTTPException

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
        with pytest.raises(HTTPException) as exc:
            verify_token(creds)
        assert exc.value.status_code == 401
