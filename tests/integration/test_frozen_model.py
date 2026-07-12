"""Frozen XGBoost test model: reproducible ranking scores (Issue #16).

The committed artifact ``tests/integration/fixtures/xgboost_test_model.json``
was trained deterministically (fixed seed, fixed synthetic data) by
``tests/integration/fixtures/make_frozen_model.py``. These tests verify that
loading the frozen model through the real ranking-engine code path yields
bit-identical scores on every run, and that the /score API serves it.

Skips cleanly when xgboost is not installed in the environment.
"""

from pathlib import Path

import pytest

xgb = pytest.importorskip("xgboost", reason="xgboost required for frozen-model tests")

from services.ranking_engine.src.main import RankingModel, ranking_model  # noqa: E402
from tests.integration.test_feed_pipeline import FIXED_FEATURE_BATCH  # noqa: E402

FROZEN_MODEL_PATH = Path(__file__).parent / "fixtures" / "xgboost_test_model.json"

# Golden scores produced by the frozen model for FIXED_FEATURE_BATCH.
# Regenerate with tests/integration/fixtures/make_frozen_model.py if the
# artifact is ever intentionally retrained.
GOLDEN_SCORES = [0.8231305480003357, 0.6133317351341248, 0.4102824330329895]


@pytest.fixture(scope="module")
def frozen_model() -> RankingModel:
    assert FROZEN_MODEL_PATH.exists(), (
        f"Frozen model artifact missing: {FROZEN_MODEL_PATH}. "
        "Regenerate with: PYTHONPATH=. python tests/integration/fixtures/make_frozen_model.py"
    )
    model = RankingModel()
    model.load_model("frozen-test", str(FROZEN_MODEL_PATH))
    assert model._models["frozen-test"] is not None, "XGBoost model failed to load"
    return model


class TestFrozenModel:
    def test_scores_match_golden_values(self, frozen_model):
        scores = frozen_model.predict(FIXED_FEATURE_BATCH, "frozen-test")
        assert scores == pytest.approx(GOLDEN_SCORES, rel=1e-5)

    def test_predictions_identical_across_calls(self, frozen_model):
        first = frozen_model.predict(FIXED_FEATURE_BATCH, "frozen-test")
        second = frozen_model.predict(FIXED_FEATURE_BATCH, "frozen-test")
        assert first == second

    def test_predictions_identical_across_reloads(self, frozen_model):
        reloaded = RankingModel()
        reloaded.load_model("frozen-test", str(FROZEN_MODEL_PATH))
        assert reloaded.predict(FIXED_FEATURE_BATCH, "frozen-test") == frozen_model.predict(
            FIXED_FEATURE_BATCH, "frozen-test"
        )

    def test_ranking_order_agrees_with_heuristic(self, frozen_model):
        """Frozen model preserves the relative ordering of the heuristic scorer."""
        model_scores = frozen_model.predict(FIXED_FEATURE_BATCH, "frozen-test")
        heuristic_scores = RankingModel._heuristic_score(FIXED_FEATURE_BATCH)

        model_order = sorted(range(len(model_scores)), key=lambda i: -model_scores[i])
        heuristic_order = sorted(
            range(len(heuristic_scores)), key=lambda i: -heuristic_scores[i]
        )
        assert model_order == heuristic_order

    async def test_score_endpoint_serves_frozen_model(self, ranking_client):
        """The /score API returns golden scores when the frozen model is loaded."""
        ranking_model.load_model("frozen-test", str(FROZEN_MODEL_PATH))
        try:
            payload = {"candidates": FIXED_FEATURE_BATCH, "model_version": "frozen-test"}
            first = await ranking_client.post("/score", json=payload)
            second = await ranking_client.post("/score", json=payload)

            assert first.status_code == 200
            assert first.json()["scores"] == pytest.approx(GOLDEN_SCORES, rel=1e-5)
            assert first.json()["scores"] == second.json()["scores"]
            assert first.json()["model_version"] == "frozen-test"
        finally:
            ranking_model._models.pop("frozen-test", None)
