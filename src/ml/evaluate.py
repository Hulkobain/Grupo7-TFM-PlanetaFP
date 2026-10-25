from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)


def evaluate(y_true, y_prob, threshold: float) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.ndim != 1 or y_prob.ndim != 1 or y_true.shape != y_prob.shape:
        raise ValueError(
            "y_true e y_prob deben ser vectores unidimensionales del mismo tamaño"
        )
    if y_true.size == 0:
        raise ValueError("No se puede evaluar un conjunto vacío")
    if not np.isin(y_true, [0, 1]).all():
        raise ValueError("y_true debe contener únicamente 0 o 1")
    if set(np.unique(y_true)) != {0, 1}:
        raise ValueError(
            "y_true debe contener ambas clases (0 y 1) para calcular ROC AUC"
        )
    if not np.isfinite(y_prob).all() or ((y_prob < 0) | (y_prob > 1)).any():
        raise ValueError("y_prob debe contener probabilidades finitas entre 0 y 1")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold debe ser un valor finito entre 0 y 1")

    y_pred = (y_prob >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "average_precision": float(average_precision_score(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "threshold": float(threshold),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }


def probability_to_percentage(probability: float) -> float:
    probability = float(probability)
    if not np.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("probability debe ser un valor finito entre 0 y 1")
    return round(100.0 * probability, 2)
