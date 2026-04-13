"""Feed response models."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RankedPost(BaseModel):
    post_id: UUID
    author_id: UUID
    content_type: str
    score: float
    position: int
    text_preview: Optional[str] = None
    media_url: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime


class FeedResponse(BaseModel):
    user_id: UUID
    posts: list[RankedPost]
    next_cursor: Optional[str] = None
    total_candidates: int = 0
    page_size: int = 0
