"""Feed scorer: computes relevance scores for candidate posts."""

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from services.feed_service.src.models.post import CandidatePost, ScoredPost


class FeedScorer:
    """Scores candidate posts using a weighted feature combination.

    In production this calls the ranking-engine service for XGBoost inference.
    This implementation provides the fallback heuristic scorer.
    """

    DEFAULT_WEIGHTS = {
        "author_affinity": 0.25,
        "engagement_velocity": 0.20,
        "recency_decay": 0.20,
        "content_type_pref": 0.15,
        "social_proof": 0.10,
        "post_quality": 0.10,
    }

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    async def score_batch(
        self,
        candidates: list[CandidatePost],
        user_preferences: dict[str, Any],
    ) -> list[ScoredPost]:
        scored = []
        for candidate in candidates:
            features = self._extract_features(candidate, user_preferences)
            score = self._compute_score(features)
            scored.append(
                ScoredPost(
                    **candidate.model_dump(),
                    score=score,
                    features=features,
                )
            )
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored

    def _extract_features(
        self, post: CandidatePost, preferences: dict[str, Any]
    ) -> dict[str, float]:
        now = datetime.now(UTC)
        age_hours = max((now - post.created_at).total_seconds() / 3600, 0.01)

        return {
            "author_affinity": self._author_affinity(post.author_id, preferences),
            "engagement_velocity": self._engagement_velocity(post),
            "recency_decay": self._recency_decay(age_hours),
            "content_type_pref": self._content_type_preference(post.content_type, preferences),
            "social_proof": self._social_proof(post),
            "post_quality": self._post_quality(post),
        }

    def _compute_score(self, features: dict[str, float]) -> float:
        return sum(self.weights.get(name, 0.0) * value for name, value in features.items())

    @staticmethod
    def _author_affinity(author_id: UUID, preferences: dict) -> float:
        """Affinity based on past interactions. Returns 0.0-1.0."""
        affinities = preferences.get("author_affinities", {})
        return float(affinities.get(str(author_id), 0.5))

    @staticmethod
    def _engagement_velocity(post: CandidatePost) -> float:
        """Normalized engagement rate in first 4 hours."""
        total = post.like_count + post.comment_count * 2 + post.share_count * 3
        age_hours = max(
            (datetime.now(UTC) - post.created_at).total_seconds() / 3600,
            0.01,
        )
        velocity = total / min(age_hours, 4.0)
        return min(velocity / 100.0, 1.0)

    @staticmethod
    def _recency_decay(age_hours: float, half_life: float = 6.0) -> float:
        """Exponential decay with configurable half-life."""
        return math.exp(-0.693 * age_hours / half_life)

    @staticmethod
    def _content_type_preference(content_type: str, preferences: dict) -> float:
        weights = preferences.get("content_weights", {})
        return float(weights.get(content_type, 0.5))

    @staticmethod
    def _social_proof(post: CandidatePost) -> float:
        """Mutual connection engagement signal."""
        return min(post.mutual_engagement_count / 10.0, 1.0)

    @staticmethod
    def _post_quality(post: CandidatePost) -> float:
        """Quality heuristic based on content richness."""
        score = 0.3
        if post.has_media:
            score += 0.3
        if post.text_length and post.text_length > 50:
            score += 0.2
        if post.hashtag_count and 1 <= post.hashtag_count <= 5:
            score += 0.2
        return min(score, 1.0)
