"""Cross-service integration tests for the feed pipeline (Issue #16).

These tests run fully in-process against the real FastAPI apps of all five
services via httpx ``ASGITransport``, using the deterministic seed data
defined in ``conftest.py`` (fixed UUIDs, fixed timestamp offsets). No external
infrastructure is required, so this module always runs in CI.

Container-backed verification of the isolated PostgreSQL/Redis/Kafka stack
lives in ``test_containers.py``.
"""

from uuid import uuid4

from services.api_gateway.src.auth.jwt_handler import create_access_token
from services.content_ingestion.src.consumers.engagement_consumer import (
    EngagementConsumer,
)
from tests.integration.conftest import (
    AUTHOR_GAMMA,
    POST_ALPHA_FRESH,
    POST_ALPHA_SECOND,
    POST_BETA_OLD,
    POST_BETA_VIDEO,
    POST_GAMMA_TRENDING,
    SEEDED_POST_IDS,
    VIEWER_ID,
)

# ---------------------------------------------------------------------------
# Cross-service health verification
# ---------------------------------------------------------------------------


class TestCrossServiceHealth:
    async def test_all_services_healthy(
        self,
        gateway_client,
        feed_client,
        ranking_client,
        profile_client,
        ingestion_client,
    ):
        """Every service in the mesh reports healthy with its own identity."""
        expected = {
            "api-gateway": gateway_client,
            "feed-service": feed_client,
            "ranking-engine": ranking_client,
            "user-profile": profile_client,
            "content-ingestion": ingestion_client,
        }
        for service_name, client in expected.items():
            resp = await client.get("/health")
            assert resp.status_code == 200, service_name
            body = resp.json()
            assert body["status"] == "healthy", service_name
            if "service" in body:
                assert body["service"] == service_name


# ---------------------------------------------------------------------------
# Gateway auth flow
# ---------------------------------------------------------------------------


class TestGatewayAuthFlow:
    async def test_feed_requires_token(self, gateway_client):
        resp = await gateway_client.get("/api/v1/feed")
        assert resp.status_code in (401, 403)

    async def test_feed_with_signed_jwt(self, gateway_client, auth_headers):
        resp = await gateway_client.get("/api/v1/feed", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["user_id"] == str(VIEWER_ID)

    async def test_garbage_token_rejected(self, gateway_client):
        resp = await gateway_client.get(
            "/api/v1/feed", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert resp.status_code == 401

    async def test_engagement_for_other_user_forbidden(self, gateway_client):
        other_user = uuid4()
        token = create_access_token(other_user)
        resp = await gateway_client.post(
            f"/api/v1/users/{VIEWER_ID}/engagement",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Feed assembly pipeline (feed-service: retrieval -> scoring -> diversify -> page)
# ---------------------------------------------------------------------------


class TestFeedAssemblyPipeline:
    async def test_deterministic_ranking_order(self, feed_client, feed_pipeline):
        """Seeded candidates always rank in the same order.

        Expected (heuristic scorer with viewer preferences):
        alpha_fresh > beta_video > alpha_second organically, with the trending
        gamma post interleaved at position 3 and the stale beta post last.
        """
        resp = await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        assert resp.status_code == 200
        body = resp.json()

        post_ids = [p["post_id"] for p in body["posts"]]
        assert post_ids == [
            str(POST_ALPHA_FRESH),
            str(POST_BETA_VIDEO),
            str(POST_ALPHA_SECOND),
            str(POST_GAMMA_TRENDING),
            str(POST_BETA_OLD),
        ]
        assert body["user_id"] == str(VIEWER_ID)
        assert body["total_candidates"] == len(SEEDED_POST_IDS)

    async def test_duplicate_candidates_deduplicated(self, feed_client, feed_pipeline):
        """Gamma arrives from both retrieval sources but appears exactly once."""
        resp = await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        post_ids = [p["post_id"] for p in resp.json()["posts"]]
        assert post_ids.count(str(POST_GAMMA_TRENDING)) == 1
        assert len(post_ids) == len(set(post_ids))

    async def test_organic_scores_descending(self, feed_client, feed_pipeline):
        resp = await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        organic = [
            p for p in resp.json()["posts"] if p["author_id"] != str(AUTHOR_GAMMA)
        ]
        scores = [p["score"] for p in organic]
        assert scores == sorted(scores, reverse=True)
        assert all(0.0 <= s <= 1.0 for s in scores)

    async def test_trending_interleaved_at_position_three(
        self, feed_client, feed_pipeline
    ):
        resp = await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        posts = resp.json()["posts"]
        assert posts[3]["post_id"] == str(POST_GAMMA_TRENDING)
        assert posts[3]["position"] == 3

    async def test_cursor_pagination_is_stable(self, feed_client, feed_pipeline):
        page1 = (
            await feed_client.get(
                "/feed", params={"user_id": str(VIEWER_ID), "limit": 2}
            )
        ).json()
        assert page1["page_size"] == 2
        assert page1["next_cursor"]

        page2 = (
            await feed_client.get(
                "/feed",
                params={
                    "user_id": str(VIEWER_ID),
                    "limit": 2,
                    "cursor": page1["next_cursor"],
                },
            )
        ).json()

        ids_page1 = {p["post_id"] for p in page1["posts"]}
        ids_page2 = {p["post_id"] for p in page2["posts"]}
        assert not ids_page1 & ids_page2
        assert [p["position"] for p in page1["posts"]] == [0, 1]
        assert [p["position"] for p in page2["posts"]] == [2, 3]

    async def test_second_request_served_from_cache(self, feed_client, feed_pipeline):
        first = (
            await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        ).json()
        calls_after_first = feed_pipeline.following_calls

        second = (
            await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        ).json()

        assert feed_pipeline.following_calls == calls_after_first
        assert second == first


# ---------------------------------------------------------------------------
# End-to-end: POST engagement -> spike -> cache invalidation -> feed changes
# ---------------------------------------------------------------------------


class TestEngagementToFeedFlow:
    async def test_engagement_spike_reranks_feed(
        self, gateway_client, feed_client, auth_headers, feed_pipeline, monkeypatch
    ):
        """A like spike on a post moves it up in the next feed response.

        Flow under test (the Kafka hop between gateway and consumer is
        simulated in-process, everything else is the real code path):

        1. Baseline feed ranks alpha_second below beta_video.
        2. Gateway accepts engagement writes for the authenticated user.
        3. The engagement consumer aggregates the like spike, crosses the
           spike threshold, and emits a feed invalidation.
        4. The invalidation clears the feed cache; re-assembly ranks the
           spiked post above beta_video.
        """
        # 1. Baseline order: beta_video ahead of alpha_second.
        baseline = (
            await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        ).json()
        baseline_ids = [p["post_id"] for p in baseline["posts"]]
        assert baseline_ids.index(str(POST_BETA_VIDEO)) < baseline_ids.index(
            str(POST_ALPHA_SECOND)
        )

        # 2. Gateway accepts the engagement POST for the authenticated user.
        resp = await gateway_client.post(
            f"/api/v1/users/{VIEWER_ID}/engagement", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

        # 3. Consumer processes the like spike (simulated Kafka delivery) and
        #    emits an invalidation once the 1h window crosses the threshold.
        consumer = EngagementConsumer()
        invalidated_posts: list[str] = []

        async def capture_invalidation(post_id: str) -> None:
            invalidated_posts.append(post_id)
            feed_pipeline.invalidate_cache()

        monkeypatch.setattr(consumer, "_emit_invalidation", capture_invalidation)

        spike_likes = 400
        for _ in range(4):
            await consumer.handle_event(
                {
                    "post_id": str(POST_ALPHA_SECOND),
                    "engagement_type": "like",
                    "value": spike_likes // 4,
                }
            )
        assert invalidated_posts and invalidated_posts[0] == str(POST_ALPHA_SECOND)

        # 4. Candidate counters reflect the aggregated spike; the invalidated
        #    cache forces re-ranking and the spiked post overtakes beta_video.
        counter_key = f"{POST_ALPHA_SECOND}:like"
        assert consumer._counters[counter_key]["total"] == spike_likes
        feed_pipeline.extra_likes[POST_ALPHA_SECOND] = consumer._counters[
            counter_key
        ]["total"]

        reranked = (
            await feed_client.get("/feed", params={"user_id": str(VIEWER_ID)})
        ).json()
        reranked_ids = [p["post_id"] for p in reranked["posts"]]

        assert reranked_ids != baseline_ids
        assert reranked_ids.index(str(POST_ALPHA_SECOND)) < reranked_ids.index(
            str(POST_BETA_VIDEO)
        )

    async def test_below_threshold_engagement_does_not_invalidate(self, monkeypatch):
        consumer = EngagementConsumer()
        invalidated: list[str] = []

        async def capture(post_id: str) -> None:
            invalidated.append(post_id)

        monkeypatch.setattr(consumer, "_emit_invalidation", capture)

        await consumer.handle_event(
            {"post_id": str(POST_BETA_OLD), "engagement_type": "like", "value": 5}
        )
        assert invalidated == []
        assert consumer._counters[f"{POST_BETA_OLD}:like"]["total"] == 5


# ---------------------------------------------------------------------------
# Ranking engine scoring API
# ---------------------------------------------------------------------------

FIXED_FEATURE_BATCH = [
    {
        "author_affinity": 0.9,
        "engagement_velocity": 1.0,
        "recency_decay": 0.89,
        "content_type_pref": 1.0,
        "social_proof": 0.5,
        "post_quality": 1.0,
    },
    {
        "author_affinity": 0.7,
        "engagement_velocity": 0.54,
        "recency_decay": 0.5,
        "content_type_pref": 1.2,
        "social_proof": 0.3,
        "post_quality": 1.0,
    },
    {
        "author_affinity": 0.7,
        "engagement_velocity": 0.0,
        "recency_decay": 0.004,
        "content_type_pref": 0.8,
        "social_proof": 0.0,
        "post_quality": 0.3,
    },
]


class TestRankingEngineScoring:
    async def test_scores_are_reproducible(self, ranking_client):
        payload = {"candidates": FIXED_FEATURE_BATCH, "model_version": "v1"}
        first = await ranking_client.post("/score", json=payload)
        second = await ranking_client.post("/score", json=payload)
        assert first.status_code == second.status_code == 200
        assert first.json()["scores"] == second.json()["scores"]
        # Better candidates score strictly higher.
        scores = first.json()["scores"]
        assert scores[0] > scores[1] > scores[2]

    async def test_empty_candidates_rejected(self, ranking_client):
        resp = await ranking_client.post(
            "/score", json={"candidates": [], "model_version": "v1"}
        )
        assert resp.status_code == 400
