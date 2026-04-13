"""Feed assembler: constructs the final paginated feed response."""
import base64
import json
from typing import Optional
from uuid import UUID

from services.feed_service.src.models.feed import FeedResponse, RankedPost
from services.feed_service.src.models.post import ScoredPost


class FeedAssembler:
    """Assembles scored/diversified posts into a paginated feed response."""

    def assemble(
        self,
        posts: list[ScoredPost],
        user_id: UUID,
        limit: int = 25,
        cursor: Optional[str] = None,
    ) -> FeedResponse:
        offset = self._decode_cursor(cursor)
        page = posts[offset : offset + limit]

        ranked_posts = [
            RankedPost(
                post_id=p.post_id,
                author_id=p.author_id,
                content_type=p.content_type,
                score=round(p.score, 4),
                position=offset + idx,
                text_preview=p.text_preview,
                media_url=p.media_url,
                like_count=p.like_count,
                comment_count=p.comment_count,
                share_count=p.share_count,
                created_at=p.created_at,
            )
            for idx, p in enumerate(page)
        ]

        next_cursor = None
        if offset + limit < len(posts):
            next_cursor = self._encode_cursor(offset + limit)

        return FeedResponse(
            user_id=user_id,
            posts=ranked_posts,
            next_cursor=next_cursor,
            total_candidates=len(posts),
            page_size=len(ranked_posts),
        )

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        payload = json.dumps({"offset": offset})
        return base64.urlsafe_b64encode(payload.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: Optional[str]) -> int:
        if not cursor:
            return 0
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            return payload.get("offset", 0)
        except Exception:
            return 0
