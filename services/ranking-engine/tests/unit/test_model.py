"""Unit tests for the ranking engine model server."""
import pytest
from services.ranking_engine.src.main import RankingModel


@pytest.fixture
def model():
    m = RankingModel()
    return m


class TestRankingModel:
    def test_heuristic_fallback(self, model):
        features = [
            {"author_affinity": 0.8, "engagement_velocity": 0.6, "recency_decay": 0.9,
             "content_type_pref": 0.7, "social_proof": 0.5, "post_quality": 0.8},
            {"author_affinity": 0.2, "engagement_velocity": 0.1, "recency_decay": 0.1,
             "content_type_pref": 0.3, "social_proof": 0.1, "post_quality": 0.2},
        ]
        scores = model.predict(features, "v1")
        assert len(scores) == 2
        assert scores[0] > scores[1]

    def test_empty_features(self, model):
        scores = model.predict([], "v1")
        assert scores == []

    def test_single_candidate(self, model):
        features = [{"author_affinity": 1.0, "recency_decay": 1.0}]
        scores = model.predict(features, "v1")
        assert len(scores) == 1
        assert scores[0] > 0

    def test_unknown_version_uses_heuristic(self, model):
        features = [{"author_affinity": 0.5}]
        scores = model.predict(features, "v999")
        assert len(scores) == 1

    def test_scores_are_deterministic(self, model):
        features = [{"author_affinity": 0.5, "engagement_velocity": 0.3}]
        s1 = model.predict(features, "v1")
        s2 = model.predict(features, "v1")
        assert s1 == s2
