"""Unit tests for the feed assembler."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from services.feed_service.src.models.post import ScoredPost
from services.feed_service.src.ranking.assembler import FeedAssembler


@pytest.fixture
def assembler():
    return FeedAssembler()


def make_scored(score=0.5):
    return ScoredPost(
        post_id=uuid4(),
        author_id=uuid4(),
        content_type="text",
        score=score,
        created_at=datetime.now(UTC),
    )


class TestFeedAssembler:
    def test_basic_assembly(self, assembler):
        posts = [make_scored(1.0 - i * 0.1) for i in range(10)]
        user_id = uuid4()
        result = assembler.assemble(posts, user_id, limit=5)
        assert result.user_id == user_id
        assert len(result.posts) == 5
        assert result.page_size == 5
        assert result.next_cursor is not None

    def test_no_next_cursor_at_end(self, assembler):
        posts = [make_scored() for _ in range(3)]
        result = assembler.assemble(posts, uuid4(), limit=10)
        assert result.next_cursor is None

    def test_cursor_pagination(self, assembler):
        posts = [make_scored(1.0 - i * 0.01) for i in range(50)]
        user_id = uuid4()

        page1 = assembler.assemble(posts, user_id, limit=25)
        assert len(page1.posts) == 25
        assert page1.next_cursor is not None

        page2 = assembler.assemble(posts, user_id, limit=25, cursor=page1.next_cursor)
        assert len(page2.posts) == 25
        assert page2.next_cursor is None

        # No overlap
        page1_ids = {p.post_id for p in page1.posts}
        page2_ids = {p.post_id for p in page2.posts}
        assert page1_ids.isdisjoint(page2_ids)

    def test_positions_are_sequential(self, assembler):
        posts = [make_scored() for _ in range(5)]
        result = assembler.assemble(posts, uuid4(), limit=5)
        positions = [p.position for p in result.posts]
        assert positions == [0, 1, 2, 3, 4]

    def test_empty_feed(self, assembler):
        result = assembler.assemble([], uuid4(), limit=25)
        assert len(result.posts) == 0
        assert result.next_cursor is None

    def test_invalid_cursor_returns_from_start(self, assembler):
        posts = [make_scored() for _ in range(5)]
        result = assembler.assemble(posts, uuid4(), limit=5, cursor="garbage")
        assert len(result.posts) == 5

    def test_total_candidates_count(self, assembler):
        posts = [make_scored() for _ in range(100)]
        result = assembler.assemble(posts, uuid4(), limit=25)
        assert result.total_candidates == 100
