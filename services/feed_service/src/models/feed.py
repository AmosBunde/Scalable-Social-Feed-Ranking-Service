"""Feed response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RankedPost(BaseModel):
    post_id: UUID
    author_id: UUID
    content_type: str
    score: float
    position: int
    text_preview: str | None = None
    media_url: str | None = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime


class FeedResponse(BaseModel):
    user_id: UUID
    posts: list[RankedPost]
    next_cursor: str | None = None
    total_candidates: int = 0
    page_size: int = 0
