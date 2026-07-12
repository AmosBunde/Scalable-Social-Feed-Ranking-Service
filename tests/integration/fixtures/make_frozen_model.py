"""Regenerate the frozen XGBoost test model (Issue #16).

Trains a tiny, fully deterministic booster on synthetic data derived from the
production heuristic weights, then saves it as JSON. The committed artifact
(``xgboost_test_model.json``) gives the ranking-engine tests reproducible,
version-pinned scores.

Usage:
    PYTHONPATH=. python tests/integration/fixtures/make_frozen_model.py
"""

from pathlib import Path

import numpy as np
import xgboost as xgb

# Must stay sorted: RankingModel.predict feeds features in sorted-name order.
FEATURE_NAMES = sorted(
    [
        "author_affinity",
        "engagement_velocity",
        "recency_decay",
        "content_type_pref",
        "social_proof",
        "post_quality",
    ]
)

HEURISTIC_WEIGHTS = {
    "author_affinity": 0.25,
    "engagement_velocity": 0.20,
    "recency_decay": 0.20,
    "content_type_pref": 0.15,
    "social_proof": 0.10,
    "post_quality": 0.10,
}

MODEL_PATH = Path(__file__).parent / "xgboost_test_model.json"


def build_model() -> xgb.Booster:
    rng = np.random.default_rng(seed=16)  # fixed seed -> deterministic artifact
    features = rng.uniform(0.0, 1.0, size=(512, len(FEATURE_NAMES)))
    weights = np.array([HEURISTIC_WEIGHTS[name] for name in FEATURE_NAMES])
    labels = features @ weights

    dtrain = xgb.DMatrix(features, label=labels, feature_names=FEATURE_NAMES)
    params = {
        "objective": "reg:squarederror",
        "max_depth": 3,
        "eta": 0.3,
        "seed": 16,
        "nthread": 1,
    }
    return xgb.train(params, dtrain, num_boost_round=20)


if __name__ == "__main__":
    model = build_model()
    model.save_model(MODEL_PATH)
    print(f"Frozen test model written to {MODEL_PATH}")
