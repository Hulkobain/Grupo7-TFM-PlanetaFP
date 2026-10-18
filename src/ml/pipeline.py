from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import load_config
from .evaluate import evaluate
from .model import build_model, save_artifact, train


def _load_cleaned(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def run(
    config_path: Path,
    data_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    config = load_config(config_path)
    if data_path is not None:
        config["data"]["cleaned_path"] = str(data_path)
    if output_dir is not None:
        config["output"]["model_dir"] = str(output_dir)

    target_col = config["data"]["target_column"]
    df = _load_cleaned(Path(config["data"]["cleaned_path"]))
    if target_col not in df.columns:
        raise ValueError(f"Columna objetivo ausente en los datos limpios: {target_col}")

    feature_names = [c for c in df.columns if c != target_col]
    X = df[feature_names]
    y = df[target_col].to_numpy()

    stratify = y if config["validation"]["stratify"] else None
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=config["validation"]["test_size"],
        random_state=config["validation"]["random_state"],
        stratify=stratify,
    )

    model, early_rounds = build_model(config)
    train(model, X_train, y_train, X_val, y_val, early_rounds)

    y_prob = model.predict_proba(X_val)[:, 1]
    metrics = evaluate(y_val, y_prob, config["model"]["threshold"])
    save_artifact(model, feature_names, metrics, config, len(X_train), len(X_val))
    return metrics
