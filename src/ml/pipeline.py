from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .evaluate import evaluate
from .model import build_model, save_artifact, train

TIMESTAMP_COLUMN = "order_timestamp"


@dataclass
class DatasetSplits:
    target_column: str
    feature_names: list[str]
    X_train: pd.DataFrame
    X_val: pd.DataFrame
    X_test: pd.DataFrame
    y_train: np.ndarray
    y_val: np.ndarray
    y_test: np.ndarray


def _load_cleaned(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _temporal_split(
    df: pd.DataFrame,
    target_col: str,
    validation_size: float,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    if TIMESTAMP_COLUMN not in df.columns:
        raise ValueError(
            f"Columna temporal obligatoria ausente en los datos limpios: {TIMESTAMP_COLUMN}"
        )
    if not 0 < validation_size < 1 or not 0 < test_size < 1:
        raise ValueError("validation_size y test_size deben estar entre 0 y 1")
    if validation_size + test_size >= 1:
        raise ValueError("validation_size + test_size debe ser menor que 1")

    timestamps = pd.to_numeric(df[TIMESTAMP_COLUMN], errors="coerce").to_numpy(
        dtype=float
    )
    if not np.isfinite(timestamps).all():
        raise ValueError(f"{TIMESTAMP_COLUMN} contiene valores vacíos o inválidos")
    y = df[target_col].to_numpy()
    if not np.isin(y, [0, 1]).all():
        raise ValueError(f"{target_col} debe contener únicamente 0 o 1")

    order = np.argsort(timestamps, kind="stable")
    n_rows = len(order)
    sorted_timestamps = timestamps[order]
    boundaries = np.flatnonzero(sorted_timestamps[1:] > sorted_timestamps[:-1]) + 1
    if len(boundaries) < 2:
        raise ValueError(
            "Se necesitan al menos tres timestamps distintos para separar train, validation y test"
        )

    train_target = n_rows * (1 - validation_size - test_size)
    validation_target = n_rows * (1 - test_size)
    train_end = int(boundaries[np.argmin(np.abs(boundaries - train_target))])
    validation_boundaries = boundaries[boundaries > train_end]
    if validation_boundaries.size == 0:
        raise ValueError("No hay suficientes fechas para separar validation y test")
    validation_end = int(
        validation_boundaries[
            np.argmin(np.abs(validation_boundaries - validation_target))
        ]
    )

    train_indices = order[:train_end]
    validation_indices = order[train_end:validation_end]
    test_indices = order[validation_end:]

    for name, indices in (
        ("train", train_indices),
        ("validation", validation_indices),
        ("test", test_indices),
    ):
        if set(np.unique(y[indices])) != {0, 1}:
            raise ValueError(
                f"El segmento temporal {name} debe contener ambas clases (0 y 1)"
            )

    feature_names = [column for column in df.columns if column != target_col]
    X = df[feature_names]
    return (
        X.iloc[train_indices],
        X.iloc[validation_indices],
        X.iloc[test_indices],
        y[train_indices],
        y[validation_indices],
        y[test_indices],
    )


def prepare_data(config: dict, data_path: Path | None = None) -> DatasetSplits:
    if data_path is not None:
        config["data"]["cleaned_path"] = str(data_path)

    target_col = config["data"]["target_column"]
    df = _load_cleaned(Path(config["data"]["cleaned_path"]))
    if target_col not in df.columns:
        raise ValueError(f"Columna objetivo ausente en los datos limpios: {target_col}")

    feature_names = [c for c in df.columns if c != target_col]
    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test,
    ) = _temporal_split(
        df,
        target_col,
        config["validation"]["validation_size"],
        config["validation"]["test_size"],
    )
    return DatasetSplits(
        target_column=target_col,
        feature_names=feature_names,
        X_train=X_train,
        X_val=X_val,
        X_test=X_test,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
    )


def run(
    config_path: Path,
    data_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    config = load_config(config_path)
    if output_dir is not None:
        config["output"]["model_dir"] = str(output_dir)

    splits = prepare_data(config, data_path)

    model, early_rounds = build_model(config)
    train(
        model,
        splits.X_train,
        splits.y_train,
        splits.X_val,
        splits.y_val,
        early_rounds,
    )

    y_prob = model.predict_proba(splits.X_test)[:, 1]
    metrics = evaluate(splits.y_test, y_prob, config["model"]["threshold"])
    save_artifact(
        model,
        splits.feature_names,
        metrics,
        config,
        len(splits.X_train),
        len(splits.X_val),
        len(splits.X_test),
    )
    return metrics
