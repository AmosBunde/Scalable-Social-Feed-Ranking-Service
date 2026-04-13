"""Unit tests for the feed scorer."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from services.feed_service.src.models.post import CandidatePost, ScoredPost
from services.feed_service.src.ranking.scorer import FeedScorer


@pytest.fixture
def scorer():
    return FeedScorer()


@pytest.fixture
def sample_post():
    return CandidatePost(
        post_id=uuid4(),
        author_id=uuid4(),
        content_type="image",
        like_count=25,
        comment_count=5,
        share_count=2,
        has_media=True,
        text_length=120,
        hashtag_count=3,
        mutual_engagement_count=4,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )


@pytest.fixture
def old_post():
    return CandidatePost(
        post_id=uuid4(),
        author_id=uuid4(),
        content_type="text",
        like_count=100,
        comment_count=20,
        share_count=10,
        has_media=False,
        text_length=200,
        hashtag_count=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )


class TestFeedScorer:
    @pytest.mark.asyncio
    async def test_score_batch_returns_sorted_scores(self, scorer, sample_post, old_post):
        candidates = [old_post, sample_post]
        scored = await scorer.score_batch(candidates, {})
        assert len(scored) == 2
        assert scored[0].score >= scored[1].score

    @pytest.mark.asyncio
    async def test_score_batch_empty_candidates(self, scorer):
        scored = await scorer.score_batch([], {})
        assert scored == []

    @pytest.mark.asyncio
    async def test_all_scores_are_positive(self, scorer, sample_post):
        scored = await scorer.score_batch([sample_post], {})
        assert all(p.score >= 0 for p in scored)

    def test_recency_decay_recent_post(self, scorer):
        decay = scorer._recency_decay(0.5)  # 30 min old
        assert 0.9 < decay <= 1.0

    def test_recency_decay_old_post(self, scorer):
        decay = scorer._recency_decay(48.0)  # 2 days old
        assert decay < 0.01

    def test_recency_decay_half_life(self, scorer):
        decay = scorer._recency_decay(6.0, half_life=6.0)
        assert abs(decay - 0.5) < 0.01

    def test_engagement_velocity_high(self, scorer):
        post = CandidatePost(
            author_id=uuid4(),
            like_count=200,
            comment_count=50,
            share_count=30,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        velocity = scorer._engagement_velocity(post)
        assert velocity > 0.5

    def test_engagement_velocity_zero(self, scorer):
        post = CandidatePost(
            author_id=uuid4(),
            like_count=0,
            comment_count=0,
            share_count=0,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        velocity = scorer._engagement_velocity(post)
        assert velocity == 0.0

    def test_post_quality_rich_content(self, scorer):
        post = CandidatePost(
            author_id=uuid4(),
            has_media=True,
            text_length=100,
            hashtag_count=3,
        )
        quality = scorer._post_quality(post)
        assert quality == 1.0

    def test_post_quality_minimal(self, scorer):
        post = CandidatePost(
            author_id=uuid4(),
            has_media=False,
            text_length=10,
            hashtag_count=0,
        )
        quality = scorer._post_quality(post)
        assert quality == 0.3

    def test_social_proof_capped_at_one(self, scorer):
        post = CandidatePost(
            author_id=uuid4(),
            mutual_engagement_count=100,
        )
        proof = scorer._social_proof(post)
        assert proof == 1.0

    def test_custom_weights(self):
        custom = {"author_affinity": 1.0}
        scorer = FeedScorer(weights=custom)
        assert scorer.weights == custom
