"""Unit tests for the feed diversifier."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from services.feed_service.src.models.post import ScoredPost
from services.feed_service.src.ranking.diversifier import FeedDiversifier


@pytest.fixture
def diversifier():
    return FeedDiversifier()


def make_post(author_id=None, content_type="text", score=0.5, is_trending=False):
    return ScoredPost(
        post_id=uuid4(),
        author_id=author_id or uuid4(),
        content_type=content_type,
        score=score,
        is_trending=is_trending,
        created_at=datetime.now(UTC),
    )


class TestFeedDiversifier:
    def test_empty_input(self, diversifier):
        assert diversifier.apply_rules([]) == []

    def test_author_diversity_enforced(self, diversifier):
        author = uuid4()
        # 5 posts from the same author interleaved with 15 from unique authors
        posts = []
        for i in range(20):
            if i % 4 == 0 and len([p for p in posts if p.author_id == author]) < 5:
                posts.append(make_post(author_id=author, score=1.0 - i * 0.01))
            else:
                posts.append(make_post(score=1.0 - i * 0.01))
        result = diversifier.apply_rules(posts)
        # In any window of 10, max 2 from the same author
        for start in range(0, max(1, len(result) - 10)):
            window = result[start : start + 10]
            count = sum(1 for p in window if p.author_id == author)
            assert count <= 2

    def test_multiple_authors_pass_through(self, diversifier):
        posts = [make_post(score=1.0 - i * 0.01) for i in range(20)]
        result = diversifier.apply_rules(posts)
        assert len(result) == 20

    def test_trending_interleaved(self, diversifier):
        organic = [make_post(score=1.0 - i * 0.01) for i in range(20)]
        trending = [make_post(is_trending=True, score=0.9) for _ in range(3)]
        all_posts = organic + trending
        result = diversifier.apply_rules(all_posts)
        # Trending posts should be at positions 3, 8, 15
        trending_positions = [i for i, p in enumerate(result) if p.is_trending]
        assert 3 in trending_positions

    def test_preserves_score_order_within_constraints(self, diversifier):
        posts = [make_post(score=1.0 - i * 0.1) for i in range(5)]
        result = diversifier.apply_rules(posts)
        non_trending = [p for p in result if not p.is_trending]
        for i in range(len(non_trending) - 1):
            assert non_trending[i].score >= non_trending[i + 1].score

    def test_single_post(self, diversifier):
        posts = [make_post()]
        result = diversifier.apply_rules(posts)
        assert len(result) == 1
