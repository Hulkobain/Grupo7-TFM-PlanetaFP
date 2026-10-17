from pathlib import Path

import pandas as pd

from src.ml.pipeline import run


def test_run_pipeline_on_cleaned_csv(tmp_path) -> None:
    df = pd.DataFrame(
        {
            "num_items": [1, 2, 3, 4, 5, 6],
            "total_value": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "Late_delivery_risk": [0, 1, 0, 1, 0, 1],
        }
    )
    cleaned = tmp_path / "cleaned.csv"
    df.to_csv(cleaned, index=False)
    out = tmp_path / "artifacts"
    metrics = run(Path("src/ml/config.yaml"), cleaned, out)
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert (out / "delay_risk_xgb.json").exists()
    assert (out / "model_metadata.json").exists()
