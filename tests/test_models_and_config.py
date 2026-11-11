import pytest
from pydantic import ValidationError

from app.config import FeatureFlags
from app.models import OptimizationRequest, RouteInput


def test_default_optimization_weights_are_valid():
    assert OptimizationRequest().model_dump() == {"cost_weight": 0.4, "time_weight": 0.3, "risk_weight": 0.3}


@pytest.mark.parametrize(
    "payload",
    [
        {"cost_weight": -0.1, "time_weight": 0.5, "risk_weight": 0.6},
        {"cost_weight": 0, "time_weight": 0, "risk_weight": 0},
    ],
)
def test_invalid_optimization_request_is_rejected(payload):
    with pytest.raises(ValidationError):
        OptimizationRequest(**payload)


def test_route_input_rejects_invalid_risk_and_negative_cost():
    base = {
        "shipment_id": "TEST", "origin": "A", "destination": "B", "route_id": "TEST-A",
        "intermediate_hubs": "Hub", "cost_inr": 1, "transit_days": 1,
        "delay_probability": 0.1, "congestion_risk": 0.1, "geopolitical_risk": 0.1,
    }
    with pytest.raises(ValidationError):
        RouteInput(**(base | {"cost_inr": 0}))
    with pytest.raises(ValidationError):
        RouteInput(**(base | {"delay_probability": 1.1}))


def test_feature_flags_use_safe_environment_values(monkeypatch):
    monkeypatch.setenv("ENABLE_OPTIMIZATION", "false")
    monkeypatch.setenv("ENABLE_PARETO_ANALYSIS", "yes")
    flags = FeatureFlags.from_environment()
    assert not flags.optimization_enabled
    assert flags.pareto_analysis_enabled


def test_unknown_flag_value_is_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_OPTIMIZATION", "maybe")
    assert not FeatureFlags.from_environment().optimization_enabled
