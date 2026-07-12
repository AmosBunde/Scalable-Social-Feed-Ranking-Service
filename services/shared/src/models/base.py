"""Shared Pydantic base models used across all services."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContentType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    POLL = "poll"


class EngagementType(StrEnum):
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    FOLLOW = "follow"
    DWELL = "dwell"
    CLICK = "click"


class BaseEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_service: str


class PostEvent(BaseEvent):
    post_id: UUID
    author_id: UUID
    content_type: ContentType
    text: str | None = None
    media_url: str | None = None
    hashtags: list[str] = Field(default_factory=list)


class EngagementEvent(BaseEvent):
    user_id: UUID
    post_id: UUID
    engagement_type: EngagementType
    value: float = 1.0
    dwell_time_ms: int | None = None


class FeedServedEvent(BaseEvent):
    user_id: UUID
    feed_size: int
    model_version: str
    latency_ms: float
    cache_hit: bool
    post_ids: list[UUID]


class UserPreferences(BaseModel):
    content_weights: dict[ContentType, float] = Field(
        default_factory=lambda: {ct: 1.0 for ct in ContentType}
    )
    muted_authors: list[UUID] = Field(default_factory=list)
    language: str = "en"


class PaginationCursor(BaseModel):
    offset: int = 0
    limit: int = 25
    cursor_token: str | None = None
