from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import xgboost as xgb


def build_model(config: dict) -> tuple[xgb.XGBClassifier, int | None]:
    hp = dict(config["model"]["hyperparams"])
    early = hp.pop("early_stopping_rounds", None)
    model = xgb.XGBClassifier(
        objective=config["model"]["objective"],
        eval_metric=config["model"]["eval_metric"],
        random_state=config["seed"],
        n_jobs=-1,
        early_stopping_rounds=early,
        **hp,
    )
    return model, early


def train(
    model: xgb.XGBClassifier,
    X_train,
    y_train,
    X_val,
    y_val,
    early_rounds: int | None,
) -> xgb.XGBClassifier:
    kwargs = {}
    if early_rounds:
        kwargs["eval_set"] = [(X_val, y_val)]
    model.fit(X_train, y_train, **kwargs)
    return model


def save_artifact(
    model: xgb.XGBClassifier,
    feature_names: list[str],
    metrics: dict,
    config: dict,
    n_train: int,
    n_val: int,
    n_test: int,
) -> tuple[Path, Path, Path]:
    out_dir = Path(config["output"]["model_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / config["output"]["model_file"]
    model.get_booster().save_model(str(model_path))

    joblib_path = out_dir / config["output"]["joblib_file"]
    joblib.dump(model, joblib_path)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": config["data"]["target_column"],
        "objective": config["model"]["objective"],
        "threshold": config["model"]["threshold"],
        "features": feature_names,
        "metrics": metrics,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "model_params": model.get_params(),
        "model_file": config["output"]["model_file"],
        "joblib_file": config["output"]["joblib_file"],
    }
    meta_path = out_dir / config["output"]["metadata_file"]
    meta_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return model_path, joblib_path, meta_path
