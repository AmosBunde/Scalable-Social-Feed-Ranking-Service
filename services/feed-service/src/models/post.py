"""Post and candidate post models."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CandidatePost(BaseModel):
    post_id: UUID = Field(default_factory=uuid4)
    author_id: UUID
    content_type: str = "text"
    text_preview: Optional[str] = None
    media_url: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    has_media: bool = False
    text_length: Optional[int] = None
    hashtag_count: int = 0
    mutual_engagement_count: int = 0
    is_trending: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScoredPost(CandidatePost):
    score: float = 0.0
    features: dict[str, float] = Field(default_factory=dict)
