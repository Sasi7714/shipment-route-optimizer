import pytest

from app.optimizer import annotate_pareto, pareto_routes
from app.scoring import _benefit_scores, combined_risk, score_routes


ROUTES = [
    {"route_id": "A", "cost_inr": 10000, "transit_days": 6, "delay_probability": 0.5, "congestion_risk": 0.5, "geopolitical_risk": 0.2},
    {"route_id": "B", "cost_inr": 18000, "transit_days": 3, "delay_probability": 0.1, "congestion_risk": 0.1, "geopolitical_risk": 0.1},
    {"route_id": "C", "cost_inr": 19000, "transit_days": 5, "delay_probability": 0.4, "congestion_risk": 0.4, "geopolitical_risk": 0.2},
]


def test_combined_risk_formula():
    assert combined_risk(ROUTES[1]) == 0.1


def test_benefit_scores_are_inverted_and_handle_equal_or_empty_values():
    assert _benefit_scores([10, 20, 30]).tolist() == [1.0, 0.5, 0.0]
    assert _benefit_scores([5, 5]).tolist() == [1.0, 1.0]
    assert _benefit_scores([]).tolist() == []


def test_weighted_scoring_ranks_routes_and_supports_changed_weights():
    cheap = score_routes(ROUTES, {"cost": 1, "time": 0, "risk": 0})
    fast_safe = score_routes(ROUTES, {"cost": 0, "time": 0.5, "risk": 0.5})
    assert cheap[0]["route_id"] == "A"
    assert fast_safe[0]["route_id"] == "B"
    assert [route["rank"] for route in cheap] == [1, 2, 3]
    assert cheap[0]["weighted_score"] >= cheap[-1]["weighted_score"]


def test_scoring_does_not_mutate_input():
    original_keys = set(ROUTES[0])
    score_routes(ROUTES)
    assert set(ROUTES[0]) == original_keys


@pytest.mark.parametrize(
    "weights",
    [
        {"cost": 0, "time": 0, "risk": 0},
        {"cost": -1, "time": 1, "risk": 1},
        {"cost": 1, "time": 1},
    ],
)
def test_invalid_internal_weights_raise_clear_error(weights):
    with pytest.raises(ValueError):
        score_routes(ROUTES, weights)


def test_empty_routes_return_empty_list():
    assert score_routes([]) == []


def test_pareto_excludes_dominated_route_and_annotation_preserves_all_routes():
    assert {route["route_id"] for route in pareto_routes(ROUTES)} == {"A", "B"}
    annotated = annotate_pareto(ROUTES)
    assert len(annotated) == 3
    assert {route["route_id"] for route in annotated if route["pareto_optimal"]} == {"A", "B"}
