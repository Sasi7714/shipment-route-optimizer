import logging

from fastapi.testclient import TestClient

import app.main as main
from app.config import FeatureFlags
from app.logging_config import logger


class MessageCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.records = []

    def emit(self, record):
        self.messages.append(record.getMessage())
        self.records.append(record)


def test_health_and_shipment_endpoints_return_data_and_request_id():
    with TestClient(main.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.headers["X-Request-ID"]

        shipments = client.get("/shipments")
        assert shipments.status_code == 200
        assert len(shipments.json()) == 20

        details = client.get("/shipments/sh001")
        assert details.status_code == 200
        assert details.json()["shipment_id"] == "SH001"

        routes = client.get("/shipments/SH002/routes")
        assert routes.status_code == 200
        assert len(routes.json()["routes"]) == 3


def test_local_dashboard_origin_is_allowed_by_cors():
    with TestClient(main.app) as client:
        response = client.options(
            "/optimize/SH001",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_optimization_returns_ranking_explanation_and_pareto_choices():
    with TestClient(main.app) as client:
        result = client.post(
            "/optimize/SH001",
            json={"cost_weight": 0.4, "time_weight": 0.3, "risk_weight": 0.3},
        )
    assert result.status_code == 200
    body = result.json()
    assert body["currency"] == "INR"
    assert len(body["routes_ranked"]) == 3
    assert body["pareto_optimal_routes"]
    assert body["recommended_route"]["weighted_score"] >= body["routes_ranked"][-1]["weighted_score"]
    assert "runner-up" in body["explanation"]


def test_comparison_uses_default_weights():
    with TestClient(main.app) as client:
        result = client.get("/optimize/SH004/comparison")
    assert result.status_code == 200
    assert result.json()["weights_used"] == {"cost": 0.4, "time": 0.3, "risk": 0.3}


def test_unknown_shipment_returns_sanitized_404():
    with TestClient(main.app) as client:
        response = client.get("/shipments/not-real")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "shipment_not_found", "message": "The requested shipment was not found."}}


def test_invalid_payload_returns_sanitized_422_without_echoing_value():
    secret = "do-not-echo-this-value"
    with TestClient(main.app) as client:
        response = client.post("/optimize/SH001", json={"cost_weight": secret})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert secret not in response.text


def test_disabled_optimization_feature_returns_503(monkeypatch):
    monkeypatch.setattr(main, "FLAGS", FeatureFlags(optimization_enabled=False, pareto_analysis_enabled=True))
    with TestClient(main.app) as client:
        response = client.post("/optimize/SH001")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "feature_disabled"


def test_disabled_pareto_feature_keeps_weighted_recommendation(monkeypatch):
    monkeypatch.setattr(main, "FLAGS", FeatureFlags(optimization_enabled=True, pareto_analysis_enabled=False))
    with TestClient(main.app) as client:
        response = client.get("/optimize/SH001/comparison")
    assert response.status_code == 200
    assert "recommended_route" in response.json()
    assert "pareto_optimal_routes" not in response.json()


def test_logs_exclude_authorization_header_and_request_body():
    collector = MessageCollector()
    logger.addHandler(collector)
    secret = "top-secret-value"
    try:
        with TestClient(main.app) as client:
            response = client.post(
                "/optimize/SH001",
                headers={"Authorization": f"Bearer {secret}"},
                json={"cost_weight": secret},
            )
        assert response.status_code == 422
    finally:
        logger.removeHandler(collector)
    assert secret not in "\n".join(collector.messages)


def test_unexpected_error_is_sanitized(monkeypatch):
    def broken_routes(*_args, **_kwargs):
        raise RuntimeError("database password: never-return-this")

    monkeypatch.setattr(main, "_routes_for", broken_routes)
    collector = MessageCollector()
    logger.addHandler(collector)
    try:
        with TestClient(main.app, raise_server_exceptions=False) as client:
            response = client.get("/shipments/SH001")
    finally:
        logger.removeHandler(collector)
    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "internal_error"
    assert "password" not in response.text
    assert body["error_id"]
    assert all(record.exc_info is None for record in collector.records)
