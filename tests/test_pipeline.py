import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from src.ml.pipeline import _temporal_split, run


def test_run_pipeline_on_cleaned_csv(tmp_path) -> None:
    n_rows = 120
    df = pd.DataFrame(
        {
            "order_timestamp": np.arange(n_rows, dtype=np.int64),
            "num_items": np.arange(1, n_rows + 1),
            "total_value": np.arange(10.0, n_rows * 10.0 + 1, 10.0),
            "Late_delivery_risk": np.arange(n_rows) % 2,
        }
    )
    cleaned = tmp_path / "cleaned.csv"
    df.to_csv(cleaned, index=False)
    out = tmp_path / "artifacts"
    metrics = run(Path("src/ml/config.yaml"), cleaned, out)
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert (out / "delay_risk_xgb.json").exists()
    assert (out / "delay_risk_xgb.joblib").exists()
    assert (out / "model_metadata.json").exists()
    restored = xgb.XGBClassifier()
    restored.load_model(str(out / "delay_risk_xgb.json"))
    assert restored.predict_proba([[1, 1, 10.0]]).shape == (1, 2)
    restored_joblib = joblib.load(out / "delay_risk_xgb.joblib")
    np.testing.assert_allclose(
        restored_joblib.predict_proba([[1, 1, 10.0]]),
        restored.predict_proba([[1, 1, 10.0]]),
    )
    metadata = json.loads((out / "model_metadata.json").read_text(encoding="utf-8"))
    assert metadata["n_train"] == 72
    assert metadata["n_val"] == 24
    assert metadata["n_test"] == 24
    assert metadata["metrics"] == metrics
    assert metadata["joblib_file"] == "delay_risk_xgb.joblib"


def test_temporal_split_keeps_test_after_validation_and_train() -> None:
    df = pd.DataFrame(
        {
            "order_timestamp": np.repeat(np.arange(10), 2),
            "feature": np.arange(20),
            "target": np.arange(20) % 2,
        }
    )

    X_train, X_val, X_test, *_ = _temporal_split(df, "target", 0.2, 0.2)

    assert X_train["order_timestamp"].max() < X_val["order_timestamp"].min()
    assert X_val["order_timestamp"].max() < X_test["order_timestamp"].min()


def test_temporal_split_rejects_missing_timestamp() -> None:
    df = pd.DataFrame({"feature": [1, 2], "target": [0, 1]})

    with pytest.raises(ValueError, match="order_timestamp"):
        _temporal_split(df, "target", 0.2, 0.2)
