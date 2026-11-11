"""Pareto optimization for cost, time and combined risk."""
from app.scoring import combined_risk


def pareto_routes(routes: list[dict]) -> list[dict]:
    """Return non-dominated routes. All three objectives are minimized."""
    prepared = [dict(route, risk_score=combined_risk(route)) for route in routes]
    optimal = []
    for candidate in prepared:
        candidate_values = (candidate["cost_inr"], candidate["transit_days"], candidate["risk_score"])
        dominated = False
        for other in prepared:
            if other["route_id"] == candidate["route_id"]:
                continue
            other_values = (other["cost_inr"], other["transit_days"], other["risk_score"])
            if all(a <= b for a, b in zip(other_values, candidate_values)) and any(
                a < b for a, b in zip(other_values, candidate_values)
            ):
                dominated = True
                break
        candidate["pareto_optimal"] = not dominated
        if not dominated:
            optimal.append(candidate)
    return optimal


def annotate_pareto(routes: list[dict]) -> list[dict]:
    ids = {route["route_id"] for route in pareto_routes(routes)}
    return [dict(route, pareto_optimal=route["route_id"] in ids) for route in routes]
