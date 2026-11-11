"""Risk calculation and weighted route scoring."""
from __future__ import annotations

import numpy as np
try:  # Scikit-learn is the primary normalizer specified for this project.
    from sklearn.preprocessing import MinMaxScaler
except ModuleNotFoundError:  # Keeps the API usable in a minimal environment before dependencies are installed.
    MinMaxScaler = None


def combined_risk(route: dict) -> float:
    """Risk in [0,1]: 50% delay, 30% congestion, 20% geopolitical exposure."""
    return round(
        0.5 * float(route["delay_probability"])
        + 0.3 * float(route["congestion_risk"])
        + 0.2 * float(route["geopolitical_risk"]),
        4,
    )


def _benefit_scores(values: list[float]) -> np.ndarray:
    """Min-max scale a cost metric and invert it: lower input means higher score."""
    if not values:
        return np.array([])
    array = np.asarray(values, dtype=float).reshape(-1, 1)
    if np.ptp(array) == 0:
        return np.ones(len(values))
    if MinMaxScaler is not None:
        scaled = MinMaxScaler().fit_transform(array).ravel()
    else:
        # Numerically identical min-max fallback; normal operation uses sklearn.
        scaled = (array.ravel() - array.min()) / (array.max() - array.min())
    return 1 - scaled


def score_routes(routes: list[dict], weights: dict | None = None) -> list[dict]:
    """Add normalized benefit scores and rank routes (largest score is best)."""
    if not routes:
        return []
    weights = weights or {"cost": 0.4, "time": 0.3, "risk": 0.3}
    expected = {"cost", "time", "risk"}
    if set(weights) != expected or any(value < 0 for value in weights.values()):
        raise ValueError("Weights must contain non-negative cost, time, and risk values.")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("At least one optimization weight must be positive.")
    normalized = {key: value / total for key, value in weights.items()}
    result = [dict(route) for route in routes]
    for route in result:
        route["risk_score"] = combined_risk(route)
    cost_scores = _benefit_scores([r["cost_inr"] for r in result])
    time_scores = _benefit_scores([r["transit_days"] for r in result])
    risk_scores = _benefit_scores([r["risk_score"] for r in result])
    for route, cost, time, risk in zip(result, cost_scores, time_scores, risk_scores):
        route["cost_score"] = round(float(cost), 4)
        route["time_score"] = round(float(time), 4)
        route["risk_benefit_score"] = round(float(risk), 4)
        route["weighted_score"] = round(
            normalized["cost"] * cost + normalized["time"] * time + normalized["risk"] * risk, 4
        )
    result.sort(key=lambda item: item["weighted_score"], reverse=True)
    for rank, route in enumerate(result, start=1):
        route["rank"] = rank
    return result
