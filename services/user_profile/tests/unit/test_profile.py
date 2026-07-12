"""Unit tests for user profile service."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from services.user_profile.src.main import UserProfile, app, store


@pytest.fixture(autouse=True)
async def clear_store():
    store._profiles.clear()
    store._graphs.clear()
    yield
    store._profiles.clear()
    store._graphs.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUserProfileService:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    async def test_get_profile_not_found(self, client):
        user_id = uuid4()
        resp = await client.get(f"/users/{user_id}")
        assert resp.status_code == 404

    async def test_get_profile_found(self, client):
        user_id = uuid4()
        profile = UserProfile(
            user_id=user_id,
            username="testuser",
            display_name="Test User",
            bio="Hello",
        )
        await store.upsert_profile(profile)
        resp = await client.get(f"/users/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["display_name"] == "Test User"

    async def test_get_graph_empty(self, client):
        user_id = uuid4()
        resp = await client.get(f"/users/{user_id}/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["following"] == []
        assert data["followers"] == []

    async def test_get_following_empty(self, client):
        user_id = uuid4()
        resp = await client.get(f"/users/{user_id}/following")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_store_upsert_and_retrieve(self):
        user_id = uuid4()
        profile = UserProfile(
            user_id=user_id,
            username="alice",
            display_name="Alice",
        )
        await store.upsert_profile(profile)
        retrieved = await store.get_profile(user_id)
        assert retrieved is not None
        assert retrieved.username == "alice"

    async def test_social_graph_follow(self):
        follower = uuid4()
        followee = uuid4()
        await store.add_follow(follower, followee)
        following = await store.get_following_ids(follower)
        assert followee in following
        graph = await store.get_graph(followee)
        assert graph is not None
        assert follower in graph.followers
