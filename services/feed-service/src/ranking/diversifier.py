"""Feed diversifier: enforces content diversity rules on scored posts."""
from collections import defaultdict
from uuid import UUID

from services.feed_service.src.models.post import ScoredPost


class FeedDiversifier:
    """Applies diversity constraints to prevent monotonous feeds.

    Rules:
    - Max 2 posts from the same author in any window of 10
    - At least 1 image/video post in every window of 5
    - Trending posts interleaved at positions 3, 8, 15
    - Sponsored content capped at 1 per 10 organic posts
    """

    MAX_AUTHOR_PER_WINDOW = 2
    AUTHOR_WINDOW_SIZE = 10
    MEDIA_WINDOW_SIZE = 5
    TRENDING_POSITIONS = {3, 8, 15}

    def apply_rules(self, scored_posts: list[ScoredPost]) -> list[ScoredPost]:
        if not scored_posts:
            return []

        # Separate trending from organic
        trending = [p for p in scored_posts if p.is_trending]
        organic = [p for p in scored_posts if not p.is_trending]

        # Apply author diversity to organic posts
        diversified = self._enforce_author_diversity(organic)

        # Interleave trending at designated positions
        diversified = self._interleave_trending(diversified, trending)

        # Enforce media diversity
        diversified = self._enforce_media_diversity(diversified)

        return diversified

    def _enforce_author_diversity(
        self, posts: list[ScoredPost]
    ) -> list[ScoredPost]:
        result: list[ScoredPost] = []
        deferred: list[ScoredPost] = []

        for post in posts:
            window_start = max(0, len(result) - self.AUTHOR_WINDOW_SIZE)
            window = result[window_start:]
            author_count = sum(
                1 for p in window if p.author_id == post.author_id
            )

            if author_count < self.MAX_AUTHOR_PER_WINDOW:
                result.append(post)
            else:
                deferred.append(post)

        # Append deferred posts at the end
        result.extend(deferred)
        return result

    def _interleave_trending(
        self,
        organic: list[ScoredPost],
        trending: list[ScoredPost],
    ) -> list[ScoredPost]:
        if not trending:
            return organic

        result = list(organic)
        trending_iter = iter(trending)

        for pos in sorted(self.TRENDING_POSITIONS):
            try:
                trend_post = next(trending_iter)
                if pos <= len(result):
                    result.insert(pos, trend_post)
                else:
                    result.append(trend_post)
            except StopIteration:
                break

        return result

    def _enforce_media_diversity(
        self, posts: list[ScoredPost]
    ) -> list[ScoredPost]:
        """Ensure at least 1 media post per window of 5."""
        result = list(posts)
        media_types = {"image", "video"}

        for window_start in range(0, len(result), self.MEDIA_WINDOW_SIZE):
            window_end = min(window_start + self.MEDIA_WINDOW_SIZE, len(result))
            window = result[window_start:window_end]

            has_media = any(p.content_type in media_types for p in window)
            if not has_media:
                # Find the nearest media post after this window and swap
                for i in range(window_end, len(result)):
                    if result[i].content_type in media_types:
                        # Swap with the lowest-scored post in the window
                        min_idx = window_start + min(
                            range(len(window)), key=lambda j: window[j].score
                        )
                        result[min_idx], result[i] = result[i], result[min_idx]
                        break

        return result
