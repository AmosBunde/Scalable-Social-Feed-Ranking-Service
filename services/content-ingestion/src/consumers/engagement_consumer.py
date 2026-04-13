"""Engagement event consumer: processes likes, comments, shares, follows."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EngagementConsumer:
    """Consumes engagement events from Kafka and updates aggregated counters.

    Aggregates engagement signals into windowed counters (1h, 24h, 7d)
    and writes enriched records to PostgreSQL. Produces feed-invalidation
    events when engagement spikes above thresholds.
    """

    SPIKE_THRESHOLDS = {
        "like": 50,
        "comment": 20,
        "share": 10,
    }

    def __init__(self):
        self._counters: dict[str, dict[str, int]] = {}

    async def handle_event(self, event: dict[str, Any]) -> None:
        post_id = event.get("post_id")
        engagement_type = event.get("engagement_type")
        value = event.get("value", 1)

        if not post_id or not engagement_type:
            logger.warning("Malformed engagement event: %s", event)
            return

        key = f"{post_id}:{engagement_type}"
        if key not in self._counters:
            self._counters[key] = {"total": 0, "window_1h": 0}

        self._counters[key]["total"] += value
        self._counters[key]["window_1h"] += value

        # Check for spike
        threshold = self.SPIKE_THRESHOLDS.get(engagement_type, 100)
        if self._counters[key]["window_1h"] >= threshold:
            logger.info(
                "Engagement spike detected for post %s: %s=%d",
                post_id, engagement_type, self._counters[key]["window_1h"]
            )
            await self._emit_invalidation(post_id)

    async def _emit_invalidation(self, post_id: str) -> None:
        """Produce a feed-invalidation event so cached feeds are refreshed."""
        logger.info("Emitting feed invalidation for post %s", post_id)
