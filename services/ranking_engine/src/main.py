"""Ranking Engine: serves XGBoost model for feed scoring."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ScoringRequest(BaseModel):
    candidates: list[dict[str, float]]
    model_version: str = "v1"


class ScoringResponse(BaseModel):
    scores: list[float]
    model_version: str


class RankingModel:
    """XGBoost model wrapper with A/B variant support."""

    def __init__(self):
        self._models: dict[str, Any] = {}
        self._default_version = "v1"

    def load_model(self, version: str, path: str) -> None:
        try:
            import xgboost as xgb

            model = xgb.Booster()
            model.load_model(path)
            self._models[version] = model
            logger.info("Loaded XGBoost model %s from %s", version, path)
        except Exception as exc:
            logger.warning("Could not load XGBoost model %s: %s. Using heuristic.", version, exc)
            self._models[version] = None

    def predict(self, features: list[dict[str, float]], version: str = "v1") -> list[float]:
        model = self._models.get(version)
        if model is None:
            return self._heuristic_score(features)

        try:
            import xgboost as xgb

            feature_names = sorted(features[0].keys()) if features else []
            matrix = np.array([[f.get(name, 0.0) for name in feature_names] for f in features])
            dmat = xgb.DMatrix(matrix, feature_names=feature_names)
            return [float(score) for score in model.predict(dmat)]
        except Exception as exc:
            logger.error("Model prediction failed: %s", exc)
            return self._heuristic_score(features)

    @staticmethod
    def _heuristic_score(features: list[dict[str, float]]) -> list[float]:
        """Fallback weighted sum scorer."""
        weights = {
            "author_affinity": 0.25,
            "engagement_velocity": 0.20,
            "recency_decay": 0.20,
            "content_type_pref": 0.15,
            "social_proof": 0.10,
            "post_quality": 0.10,
        }
        return [sum(weights.get(k, 0) * v for k, v in f.items()) for f in features]


ranking_model = RankingModel()


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = os.getenv("RANKING_MODEL_PATH", "/models/xgboost_v1.json")
    if os.path.exists(model_path):
        ranking_model.load_model("v1", model_path)
    yield


app = FastAPI(title="Ranking Engine", version="1.0.0", lifespan=lifespan)


@app.post("/score", response_model=ScoringResponse)
async def score_candidates(request: ScoringRequest):
    if not request.candidates:
        raise HTTPException(status_code=400, detail="No candidates provided")

    scores = ranking_model.predict(request.candidates, request.model_version)
    return ScoringResponse(scores=scores, model_version=request.model_version)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ranking-engine"}
