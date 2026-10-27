import json

import httpx
import pytest
from fastapi.testclient import TestClient

import src.api.main as api_main
from src.api.main import app
from src.api.schemas import PredictionResponse


SHIPMENT = {
    "order_date": "2026-10-16T10:30:00Z",
    "shipping_mode": "Standard Class",
    "customer_segment": "Consumer",
    "market": "Europe",
    "order_region": "Western Europe",
    "order_items": [
        {
            "product_category_id": 12,
            "product_price": 49.99,
            "order_item_quantity": 2,
            "order_item_discount": 5.0,
        },
        {
            "product_category_id": 24,
            "product_price": 19.99,
            "order_item_quantity": 1,
            "order_item_discount": 0.0,
        },
    ],
}


class StubInferenceService:
    def __init__(self, prediction: PredictionResponse | None = None) -> None:
        self.shipment = None
        self.prediction = prediction or PredictionResponse(
            delay_risk=True,
            delay_probability=0.75,
            threshold=0.5,
        )

    def predict(self, shipment: dict) -> PredictionResponse:
        self.shipment = shipment
        return self.prediction


def create_client(monkeypatch, inference_service=None, transport=None) -> TestClient:
    monkeypatch.setattr(
        api_main,
        "load_inference_service",
        lambda: inference_service,
    )
    if transport is not None:
        monkeypatch.setattr(
            api_main,
            "create_webhook_client",
            lambda: httpx.AsyncClient(transport=transport),
        )
    return TestClient(app)


def test_health_returns_ok(monkeypatch) -> None:
    with create_client(monkeypatch) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_returns_prediction_for_validated_shipment(monkeypatch) -> None:
    inference_service = StubInferenceService()
    with create_client(monkeypatch, inference_service) as client:
        response = client.post("/ingest", json=SHIPMENT)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["shipment"]["shipping_mode"] == "Standard Class"
    assert len(response.json()["shipment"]["order_items"]) == 2
    assert response.json()["prediction"] == {
        "delay_risk": True,
        "delay_probability": 0.75,
        "threshold": 0.5,
        "interpretation": (
            "Aviso preventivo, no confirmación de que el pedido vaya a retrasarse."
        ),
    }
    assert inference_service.shipment["shipping_mode"] == "Standard Class"


def test_ingest_rejects_invalid_and_unexpected_fields(monkeypatch) -> None:
    invalid_shipment = {
        **SHIPMENT,
        "customer_email": "customer@example.com",
        "order_items": [{**SHIPMENT["order_items"][0], "order_item_quantity": 0}],
    }

    with create_client(monkeypatch) as client:
        response = client.post("/ingest", json=invalid_shipment)

    assert response.status_code == 422


def test_ingest_requires_at_least_one_order_item(monkeypatch) -> None:
    with create_client(monkeypatch) as client:
        response = client.post("/ingest", json={**SHIPMENT, "order_items": []})

    assert response.status_code == 422


def test_ingest_reports_unavailable_model(monkeypatch) -> None:
    with create_client(monkeypatch) as client:
        response = client.post("/ingest", json=SHIPMENT)

    assert response.status_code == 503
    assert response.json() == {"detail": "Prediction model is not configured."}


@pytest.mark.parametrize("endpoint", ["/ingest", "/predict"])
def test_inference_endpoints_send_webhook_when_threshold_is_exceeded(
    monkeypatch,
    endpoint: str,
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    transport = httpx.MockTransport(handle_request)
    with create_client(
        monkeypatch,
        StubInferenceService(),
        transport,
    ) as client:
        response = client.post("/ingest", json=SHIPMENT)

    assert response.status_code == 200
    assert len(requests) == 1
    assert str(requests[0].url) == "https://example.test/alerts"
    payload = json.loads(requests[0].read())
    assert payload["event"] == "shipment.delay_risk.preventive_alert"
    assert payload["shipment"]["shipping_mode"] == "Standard Class"
    assert payload["prediction"]["delay_risk"] is True
    assert payload["prediction"]["threshold"] == 0.5


def test_inference_does_not_send_webhook_below_threshold(monkeypatch) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    service = StubInferenceService(
        PredictionResponse(
            delay_risk=False,
            delay_probability=0.49,
            threshold=0.5,
        )
    )
    transport = httpx.MockTransport(handle_request)
    with create_client(monkeypatch, service, transport) as client:
        response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 200
    assert response.json()["delay_risk"] is False
    assert requests == []


def test_webhook_failure_does_not_fail_prediction(monkeypatch) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.test/alerts")
    monkeypatch.setenv("WEBHOOK_MAX_ATTEMPTS", "1")
    requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503)

    transport = httpx.MockTransport(handle_request)
    with create_client(
        monkeypatch,
        StubInferenceService(),
        transport,
    ) as client:
        response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 200
    assert response.json()["delay_risk"] is True
    assert len(requests) == 1


def test_predict_returns_model_prediction(monkeypatch) -> None:
    inference_service = StubInferenceService()
    with create_client(monkeypatch, inference_service) as client:
        response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 200
    assert response.json() == {
        "delay_risk": True,
        "delay_probability": 0.75,
        "threshold": 0.5,
        "interpretation": (
            "Aviso preventivo, no confirmación de que el pedido vaya a retrasarse."
        ),
    }
    assert inference_service.shipment["order_items"][0]["product_category_id"] == 12


def test_predict_reports_unavailable_model(monkeypatch) -> None:
    with create_client(monkeypatch) as client:
        response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 503
    assert response.json() == {"detail": "Prediction model is not configured."}


def test_predict_validates_request_before_model_availability(monkeypatch) -> None:
    with create_client(monkeypatch) as client:
        response = client.post("/predict", json={})

    assert response.status_code == 422
