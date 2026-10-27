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
    def __init__(self) -> None:
        self.shipment = None

    def predict(self, shipment: dict) -> PredictionResponse:
        self.shipment = shipment
        return PredictionResponse(
            delay_risk=True,
            delay_probability=0.75,
            threshold=0.5,
        )


def create_client(monkeypatch, inference_service=None) -> TestClient:
    monkeypatch.setattr(
        api_main,
        "load_inference_service",
        lambda: inference_service,
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
