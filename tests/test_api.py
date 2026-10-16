from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

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


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_returns_validated_normalized_shipment() -> None:
    response = client.post("/ingest", json=SHIPMENT)

    assert response.status_code == 200
    assert response.json()["status"] == "validated"
    assert response.json()["shipment"]["shipping_mode"] == "Standard Class"
    assert len(response.json()["shipment"]["order_items"]) == 2


def test_ingest_rejects_invalid_and_unexpected_fields() -> None:
    invalid_shipment = {
        **SHIPMENT,
        "customer_email": "customer@example.com",
        "order_items": [{**SHIPMENT["order_items"][0], "order_item_quantity": 0}],
    }

    response = client.post("/ingest", json=invalid_shipment)

    assert response.status_code == 422


def test_ingest_requires_at_least_one_order_item() -> None:
    response = client.post("/ingest", json={**SHIPMENT, "order_items": []})

    assert response.status_code == 422


def test_predict_reports_unavailable_model() -> None:
    response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 503
    assert response.json() == {"detail": "Prediction model is not configured."}


def test_predict_validates_request_before_model_availability() -> None:
    response = client.post("/predict", json={})

    assert response.status_code == 422
