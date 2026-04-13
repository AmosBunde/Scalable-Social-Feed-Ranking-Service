# ADR 003: XGBoost for Feed Ranking

## Status
Accepted

## Context
The ranking pipeline needs an ML model that scores ~300 candidate posts per request with low latency. The model must learn from engagement signals (click-through, dwell time) and support A/B experimentation.

## Decision
Use XGBoost for the ranking model with 6 feature groups (author affinity, engagement velocity, recency decay, content type preference, social proof, post quality). Serve via a lightweight FastAPI endpoint with heuristic fallback.

## Consequences
- **Positive**: XGBoost batch inference at ~15ms for 300 candidates. Interpretable feature importances. Well-supported in Python ecosystem. Small model files (<10MB).
- **Negative**: Requires feature engineering pipeline. Model retraining cadence must match engagement pattern shifts.
- **Mitigated**: Heuristic weighted sum fallback ensures the service stays up even without a trained model. A/B variant support allows safe model rollout.
