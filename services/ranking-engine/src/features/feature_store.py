"""Feature store: manages engagement features for the ranking pipeline."""
import logging
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class FeatureStore:
    """Manages engagement feature vectors with windowed aggregations.

    Features are stored in Redis with TTLs and backed by PostgreSQL for
    historical training data. Supports 1h, 24h, and 7d windows.
    """

    WINDOWS = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}

    def __init__(self):
        self._cache: dict[str, dict[str, float]] = {}
        self._redis = None

    async def get_post_features(self, post_id: UUID) -> dict[str, float]:
        """Retrieve engagement features for a post across all windows."""
        key = f"features:post:{post_id}"

        if self._redis:
            cached = await self._redis.get(key)
            if cached:
                return cached

        return self._cache.get(key, self._default_features())

    async def update_features(
        self, post_id: UUID, engagement_type: str, value: float = 1.0
    ) -> None:
        """Increment engagement counters for a post."""
        key = f"features:post:{post_id}"
        features = await self.get_post_features(post_id)

        for window in self.WINDOWS:
            counter_key = f"{engagement_type}_{window}"
            features[counter_key] = features.get(counter_key, 0.0) + value

        features["total_engagements"] = features.get("total_engagements", 0.0) + value
        self._cache[key] = features

        if self._redis:
            await self._redis.set(key, features, ttl=timedelta(hours=1))

    async def get_user_features(self, user_id: UUID) -> dict[str, float]:
        """Retrieve user-level features (activity rate, preference signals)."""
        key = f"features:user:{user_id}"
        return self._cache.get(key, {"activity_rate": 0.5, "session_frequency": 0.5})

    @staticmethod
    def _default_features() -> dict[str, float]:
        return {
            "like_1h": 0.0, "like_24h": 0.0, "like_7d": 0.0,
            "comment_1h": 0.0, "comment_24h": 0.0, "comment_7d": 0.0,
            "share_1h": 0.0, "share_24h": 0.0, "share_7d": 0.0,
            "total_engagements": 0.0,
        }
