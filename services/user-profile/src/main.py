"""User Profile Service: manages user data and social graph."""
import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    user_id: UUID
    username: str
    display_name: str
    bio: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    content_weights: dict[str, float] = Field(
        default_factory=lambda: {"text": 1.0, "image": 1.2, "video": 1.1, "link": 0.8}
    )
    muted_authors: list[UUID] = Field(default_factory=list)


class SocialGraph(BaseModel):
    user_id: UUID
    following: list[UUID] = Field(default_factory=list)
    followers: list[UUID] = Field(default_factory=list)
    mutual_connections: list[UUID] = Field(default_factory=list)


class UserProfileStore:
    """In-memory user store. PostgreSQL-backed in production."""

    def __init__(self):
        self._profiles: dict[UUID, UserProfile] = {}
        self._graphs: dict[UUID, SocialGraph] = {}

    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        return self._profiles.get(user_id)

    async def get_graph(self, user_id: UUID) -> Optional[SocialGraph]:
        return self._graphs.get(user_id)

    async def get_following_ids(self, user_id: UUID) -> list[UUID]:
        graph = self._graphs.get(user_id)
        return graph.following if graph else []

    async def upsert_profile(self, profile: UserProfile) -> None:
        self._profiles[profile.user_id] = profile

    async def add_follow(self, follower_id: UUID, followee_id: UUID) -> None:
        if follower_id not in self._graphs:
            self._graphs[follower_id] = SocialGraph(user_id=follower_id)
        if followee_id not in self._graphs:
            self._graphs[followee_id] = SocialGraph(user_id=followee_id)
        self._graphs[follower_id].following.append(followee_id)
        self._graphs[followee_id].followers.append(follower_id)


store = UserProfileStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="User Profile Service", version="1.0.0", lifespan=lifespan)


@app.get("/users/{user_id}", response_model=UserProfile)
async def get_profile(user_id: UUID):
    profile = await store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@app.get("/users/{user_id}/graph", response_model=SocialGraph)
async def get_graph(user_id: UUID):
    graph = await store.get_graph(user_id)
    if not graph:
        return SocialGraph(user_id=user_id)
    return graph


@app.get("/users/{user_id}/following", response_model=list[UUID])
async def get_following(user_id: UUID):
    return await store.get_following_ids(user_id)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user-profile"}
