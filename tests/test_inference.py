import json

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient

from src.api.inference import InferenceService, load_inference_service
from src.api.main import app
from src.api.schemas import PredictionResponse
from src.data.clean import ORDER_LEVEL_FEATURES

SHIPMENT = {
    "order_date": "2026-10-16T10:30:00+00:00",
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


class FixedProbabilityModel:
    def __init__(self) -> None:
        self.features: pd.DataFrame | None = None

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        self.features = features
        return np.array([[0.25, 0.75]])


def test_inference_transforms_shipment_and_applies_model_threshold() -> None:
    feature_names = [
        *ORDER_LEVEL_FEATURES,
        "category_12_items",
        "category_24_items",
        "Shipping Mode_Standard Class",
        "Customer Segment_Consumer",
        "Market_Europe",
        "Order Region_Western Europe",
    ]
    model = FixedProbabilityModel()
    service = InferenceService(model, feature_names, threshold=0.7)

    prediction = service.predict(SHIPMENT)

    assert prediction == PredictionResponse(
        delay_risk=True,
        delay_probability=0.75,
        threshold=0.7,
    )
    assert model.features is not None
    assert model.features.columns.tolist() == feature_names
    assert model.features.loc[0, "num_items"] == 2
    assert model.features.loc[0, "total_quantity"] == 3
    assert model.features.loc[0, "category_12_items"] == 1
    assert model.features.loc[0, "category_24_items"] == 1


def test_api_predicts_with_native_xgboost_artifact(tmp_path, monkeypatch) -> None:
    feature_names = [
        *ORDER_LEVEL_FEATURES,
        "category_12_items",
        "category_24_items",
        "Shipping Mode_Standard Class",
        "Customer Segment_Consumer",
        "Market_Europe",
        "Order Region_Western Europe",
    ]
    training_features = pd.DataFrame(
        [np.zeros(len(feature_names)), np.ones(len(feature_names))],
        columns=feature_names,
    )
    model = xgb.XGBClassifier(
        n_estimators=2,
        max_depth=1,
        n_jobs=1,
        eval_metric="logloss",
    )
    model.fit(training_features, [0, 1])
    model_path = tmp_path / "delay_risk_xgb.json"
    model.save_model(model_path)
    (tmp_path / "model_metadata.json").write_text(
        json.dumps(
            {
                "model_file": model_path.name,
                "features": feature_names,
                "threshold": 0.5,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))

    with TestClient(app) as client:
        response = client.post("/predict", json=SHIPMENT)

    assert response.status_code == 200
    prediction = response.json()
    assert 0 <= prediction["delay_probability"] <= 1
    assert prediction["threshold"] == 0.5
    assert prediction["delay_risk"] == (
        prediction["delay_probability"] >= prediction["threshold"]
    )
    assert "no confirmación" in prediction["interpretation"]


def test_load_inference_service_reports_missing_artifacts(tmp_path) -> None:
    assert load_inference_service(tmp_path) is None


def test_load_inference_service_rejects_invalid_metadata(tmp_path) -> None:
    (tmp_path / "model_metadata.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="objeto JSON"):
        load_inference_service(tmp_path)
