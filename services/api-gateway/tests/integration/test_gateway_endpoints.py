"""Integration tests for API gateway endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from services.api_gateway.src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestGatewayEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_ready(self, client):
        resp = await client.get("/ready")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_feed_requires_auth(self, client):
        resp = await client.get("/api/v1/feed")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_feed_with_dev_token(self, client):
        resp = await client.get(
            "/api/v1/feed?user_id=00000000-0000-0000-0000-000000000001",
            headers={"Authorization": "Bearer dev-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "posts" in data

    @pytest.mark.asyncio
    async def test_rate_limit_header(self, client):
        resp = await client.get(
            "/api/v1/feed?user_id=00000000-0000-0000-0000-000000000001",
            headers={"Authorization": "Bearer dev-token"},
        )
        assert "x-ratelimit-remaining" in resp.headers
