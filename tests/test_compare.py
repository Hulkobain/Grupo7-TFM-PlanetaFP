import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ml.compare import _build_verdict, run_comparison


def test_run_comparison_trains_both_models_on_same_split(tmp_path) -> None:
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

    report = run_comparison(Path("src/ml/config.yaml"), cleaned, out)

    assert set(report["models"]) == {"xgboost", "lightgbm"}
    for name in ("xgboost", "lightgbm"):
        metrics = report["models"][name]["metrics"]
        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["average_precision"] <= 1.0
        assert report["models"][name]["train_seconds"] >= 0.0
    assert report["dataset"]["n_train"] == 72
    assert report["dataset"]["n_val"] == 24
    assert report["dataset"]["n_test"] == 24
    assert report["verdict"]["selected"] in {"xgboost", "lightgbm"}
    assert report["verdict"]["champion"] == "xgboost"
    assert report["verdict"]["challenger"] == "lightgbm"

    stored = json.loads(
        (out / "model_comparison.json").read_text(encoding="utf-8")
    )
    assert stored == report


def _models(roc_auc_xgb: float, roc_auc_lgbm: float) -> dict:
    return {
        "xgboost": {
            "metrics": {"roc_auc": roc_auc_xgb, "log_loss": 0.5},
            "train_seconds": 2.0,
        },
        "lightgbm": {
            "metrics": {"roc_auc": roc_auc_lgbm, "log_loss": 0.4},
            "train_seconds": 1.0,
        },
    }


def test_verdict_keeps_champion_without_material_improvement() -> None:
    verdict = _build_verdict(_models(0.80, 0.804), "roc_auc", 0.005)

    assert verdict["selected"] == "xgboost"
    assert verdict["improvement"] == pytest.approx(0.004)


def test_verdict_selects_challenger_with_material_improvement() -> None:
    verdict = _build_verdict(_models(0.80, 0.81), "roc_auc", 0.005)

    assert verdict["selected"] == "lightgbm"
    assert verdict["improvement"] == pytest.approx(0.01)


def test_verdict_handles_lower_is_better_metric() -> None:
    report_models = _models(0.80, 0.80)
    report_models["xgboost"]["metrics"]["log_loss"] = 0.42
    report_models["lightgbm"]["metrics"]["log_loss"] = 0.40

    verdict = _build_verdict(report_models, "log_loss", 0.005)

    assert verdict["selected"] == "lightgbm"
    assert verdict["higher_is_better"] is False
    assert verdict["improvement"] == pytest.approx(0.02)
